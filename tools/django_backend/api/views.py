import io
import os
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
import fitz
import cv2
import numpy as np

MAX_PDF_BYTES = 50 * 1024

@csrf_exempt
def process_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    def parse_int(name, default):
        value = request.POST.get(name, None)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_extension(filename):
        if not filename:
            return ''
        return os.path.splitext(filename)[1].lower()

    def pad_pdf_bytes(pdf_bytes, target_bytes):
        current = len(pdf_bytes)
        if current >= target_bytes:
            return pdf_bytes
        need = min(target_bytes - current, MAX_PDF_BYTES - current)
        if need <= 0:
            return pdf_bytes

        eof = b'%%EOF'
        eof_at = pdf_bytes.rfind(eof)
        if eof_at == -1:
            return pdf_bytes

        header = b"\n% PAD "
        pad_len = max(0, need - len(header) - 1)
        pad_bytes = header + b'X' * pad_len + b'\n'
        out = pdf_bytes[:eof_at] + pad_bytes + pdf_bytes[eof_at:]
        return out

    def build_pdf_from_images(image_streams, source_dpi=96.0):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer)
        c.setPageCompression(1)
        for image_data in image_streams:
            img_reader = ImageReader(io.BytesIO(image_data))
            img_width, img_height = img_reader.getSize()
            page_width = img_width * 72.0 / source_dpi
            page_height = img_height * 72.0 / source_dpi
            c.setPageSize((page_width, page_height))
            c.drawImage(img_reader, 0, 0, width=page_width, height=page_height)
            c.showPage()
        c.save()
        return buffer.getvalue()

    def optimize_pdf_bytes(file_bytes):
        doc = fitz.open(stream=file_bytes, filetype='pdf')
        buffer = io.BytesIO()
        doc.save(buffer, garbage=4, deflate=True, clean=True, incremental=False, linear=False)
        doc.close()
        return buffer.getvalue()

    def render_pdf_pages(file_bytes, dpi):
        doc = fitz.open(stream=file_bytes, filetype='pdf')
        images = []
        for page in doc:
            mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            images.append(image)
        doc.close()
        return images

    def generate_image_pdf_candidates(file_bytes, target_bytes, min_bytes, max_bytes):
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        candidates = []
        # Try a sequence of scale reductions and JPEG qualities. Also try
        # grayscale conversion as an inexpensive fallback for scanned forms.
        scales = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4]
        qualities = [80, 70, 60, 50, 45, 40, 35, 30, 25, 20, 15, 12, 10]

        # First pass: color JPEGs
        for scale in scales:
            try:
                if scale != 1.0:
                    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
                    candidate_img = img.resize(new_size, Image.Resampling.LANCZOS)
                else:
                    candidate_img = img

                for quality in qualities:
                    temp = io.BytesIO()
                    candidate_img.save(temp, format='JPEG', quality=quality, optimize=True)
                    pdf_bytes = build_pdf_from_images([temp.getvalue()])
                    if len(pdf_bytes) < min_bytes:
                        pdf_bytes = pad_pdf_bytes(pdf_bytes, min_bytes)
                    if len(pdf_bytes) <= max_bytes:
                        candidates.append((pdf_bytes, len(pdf_bytes), quality, scale))
                        # Stop early for this scale if we found a valid candidate near target
                        if abs(len(pdf_bytes) - target_bytes) <= (0.05 * target_bytes):
                            return candidates
            except Exception:
                continue

        # Second pass: try grayscale conversion which often helps scanned monochrome forms
        try:
            gray = img.convert('L')
            for scale in scales:
                if scale != 1.0:
                    new_size = (max(1, int(gray.width * scale)), max(1, int(gray.height * scale)))
                    candidate_img = gray.resize(new_size, Image.Resampling.LANCZOS)
                else:
                    candidate_img = gray

                # Convert back to RGB for JPEG encoding while keeping grayscale content
                candidate_img_rgb = candidate_img.convert('RGB')
                for quality in qualities:
                    temp = io.BytesIO()
                    candidate_img_rgb.save(temp, format='JPEG', quality=quality, optimize=True)
                    pdf_bytes = build_pdf_from_images([temp.getvalue()])
                    if len(pdf_bytes) < min_bytes:
                        pdf_bytes = pad_pdf_bytes(pdf_bytes, min_bytes)
                    if len(pdf_bytes) <= max_bytes:
                        candidates.append((pdf_bytes, len(pdf_bytes), quality, scale))
                        if abs(len(pdf_bytes) - target_bytes) <= (0.05 * target_bytes):
                            return candidates
        except Exception:
            pass

        return candidates

    def generate_pdf_candidates(file_bytes, target_bytes, min_bytes, max_bytes):
        candidates = []

        try:
            optimized = optimize_pdf_bytes(file_bytes)
            if len(optimized) < min_bytes:
                optimized = pad_pdf_bytes(optimized, min_bytes)
            if len(optimized) <= max_bytes:
                candidates.append((optimized, len(optimized), 'optimized', 0))
        except Exception:
            pass

        dpi_steps = [150, 120, 100, 90, 80, 72]
        qualities = [80, 70, 60, 50, 45, 40, 35, 30, 25, 20, 15, 12, 10]
        scales = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5]

        # Try rendering pages at several DPIs and compressing with multiple
        # JPEG qualities and optional downscaling. Stop early if a good
        # candidate near the target is found.
        for dpi in dpi_steps:
            try:
                rendered_pages = render_pdf_pages(file_bytes, dpi)
            except Exception:
                continue
            if not rendered_pages:
                continue
            for scale in scales:
                for quality in qualities:
                    image_streams = []
                    valid_candidate = True
                    for page_img in rendered_pages:
                        try:
                            # Optionally downscale page image before JPEG encoding
                            if scale != 1.0:
                                new_size = (max(1, int(page_img.width * scale)), max(1, int(page_img.height * scale)))
                                page_to_save = page_img.resize(new_size, Image.Resampling.LANCZOS)
                            else:
                                page_to_save = page_img

                            temp = io.BytesIO()
                            page_to_save.save(temp, format='JPEG', quality=quality, optimize=True)
                        except Exception:
                            valid_candidate = False
                            break
                        image_streams.append(temp.getvalue())

                    if not valid_candidate:
                        continue

                    pdf_bytes = build_pdf_from_images(image_streams, source_dpi=dpi)
                    if len(pdf_bytes) < min_bytes:
                        pdf_bytes = pad_pdf_bytes(pdf_bytes, min_bytes)
                    if len(pdf_bytes) <= max_bytes:
                        candidates.append((pdf_bytes, len(pdf_bytes), quality, dpi))
                        if abs(len(pdf_bytes) - target_bytes) <= (0.05 * target_bytes):
                            return candidates

            # Second pass for grayscale versions of rendered pages (helps scanned forms)
            try:
                gray_pages = [p.convert('L').convert('RGB') for p in rendered_pages]
                for scale in scales:
                    for quality in qualities:
                        image_streams = []
                        valid_candidate = True
                        for page_img in gray_pages:
                            try:
                                if scale != 1.0:
                                    new_size = (max(1, int(page_img.width * scale)), max(1, int(page_img.height * scale)))
                                    page_to_save = page_img.resize(new_size, Image.Resampling.LANCZOS)
                                else:
                                    page_to_save = page_img
                                temp = io.BytesIO()
                                page_to_save.save(temp, format='JPEG', quality=quality, optimize=True)
                            except Exception:
                                valid_candidate = False
                                break
                            image_streams.append(temp.getvalue())

                        if not valid_candidate:
                            continue

                        pdf_bytes = build_pdf_from_images(image_streams, source_dpi=dpi)
                        if len(pdf_bytes) < min_bytes:
                            pdf_bytes = pad_pdf_bytes(pdf_bytes, min_bytes)
                        if len(pdf_bytes) <= max_bytes:
                            candidates.append((pdf_bytes, len(pdf_bytes), quality, dpi))
                            if abs(len(pdf_bytes) - target_bytes) <= (0.05 * target_bytes):
                                return candidates
            except Exception:
                pass
        return candidates

    def choose_best_candidate(candidates, target_bytes):
        best = None
        best_dist = None
        best_size = None
        for pdf_bytes, size, quality, scale in candidates:
            dist = abs(size - target_bytes)
            if best is None or dist < best_dist or (dist == best_dist and (best_size is None or size < best_size)):
                best = pdf_bytes
                best_dist = dist
                best_size = size
        return best

    try:
        width = parse_int('width', 132)
        height = parse_int('height', 170)
        target_size_kb = parse_int('targetSize', 45)
        threshold_kb = parse_int('threshold', target_size_kb + 5)
        ideal_kb = parse_int('ideal', target_size_kb - 1)
        dpi = parse_int('dpi', 270)
        resize_algo = request.POST.get('resizeAlgorithm', 'Lanczos3')
        document_type = request.POST.get('documentType', '')

        uploaded_file = request.FILES.get('image')
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)

        filename = getattr(uploaded_file, 'name', '')
        extension = get_extension(filename)
        file_size = uploaded_file.size
        logger = logging.getLogger(__name__)
        logger.debug('Processing upload', extra={
            'filename': filename,
            'extension': extension,
            'size': file_size,
            'documentType': document_type,
        })

        if not filename or not extension:
            return JsonResponse({'error': 'Consent Form filename is missing or invalid.'}, status=400)

        if file_size <= 0:
            return JsonResponse({'error': 'Consent Form file is empty or unreadable.'}, status=400)

        if document_type == 'consent_form':
            file_bytes = uploaded_file.read()
            target_bytes = target_size_kb * 1024
            min_bytes = 20 * 1024
            max_bytes = 50 * 1024

            if extension in ('.jpg', '.jpeg', '.png'):
                try:
                    candidates = generate_image_pdf_candidates(file_bytes, target_bytes, min_bytes, max_bytes)
                except Exception as err:
                    logger.exception('Consent image processing failed')
                    return JsonResponse({'error': 'Unable to process consent form image.'}, status=500)
            elif extension == '.pdf':
                try:
                    candidates = generate_pdf_candidates(file_bytes, target_bytes, min_bytes, max_bytes)
                except Exception as err:
                    logger.exception('Consent PDF processing failed')
                    return JsonResponse({'error': 'Unable to process consent form PDF.'}, status=500)
            else:
                return JsonResponse({'error': 'Unsupported Consent Form format. Please upload JPG, JPEG, PNG, or PDF.'}, status=400)

            best_pdf = choose_best_candidate(candidates, target_bytes)
            if not best_pdf:
                return JsonResponse({'error': 'Unable to compress Consent Form into a valid 20–50 KB PDF without degrading content.'}, status=400)

            response = HttpResponse(best_pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="processed_consent_form.pdf"'
            response['X-Processed-Size'] = str(len(best_pdf))
            response['X-Processed-Format'] = 'PDF'
            response['X-Compression-Status'] = 'success'
            response['Access-Control-Expose-Headers'] = 'X-Processed-Size, X-Processed-Format, X-Compression-Status, Content-Disposition'
            return response

        image_file = uploaded_file
        img = Image.open(image_file)
        
        # Convert to RGB, handling transparency
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA' or img.mode == 'LA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Resizing
        if resize_algo == 'INTER_AREA':
            open_cv_image = np.array(img)
            open_cv_image = open_cv_image[:, :, ::-1].copy() # RGB to BGR
            resized = cv2.resize(open_cv_image, (width, height), interpolation=cv2.INTER_AREA)
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(resized)
        elif resize_algo == 'Bicubic Sharper':
            img = img.resize((width, height), resample=Image.Resampling.BICUBIC)
        else: # Default Lanczos3
            img = img.resize((width, height), resample=Image.Resampling.LANCZOS)
            
        # Smart Compression Logic
        threshold_bytes = threshold_kb * 1024
        original_size_bytes = image_file.size
        
        quality = 100
        output_io = io.BytesIO()
        img.save(output_io, format='JPEG', quality=quality, dpi=(dpi, dpi))
        size = output_io.tell()
        
        status = "unknown"
        
        if original_size_bytes <= threshold_bytes:
            # Case 1: Original upload is small
            status = "original_small"
        else:
            # Case 2: Original is large
            if size <= (ideal_kb + 1) * 1024:
                # Naturally small at Q=100
                status = "naturally_small"
            else:
                # Needs compression
                while quality >= 10:
                    output_io.seek(0)
                    output_io.truncate()
                    img.save(output_io, format='JPEG', quality=quality, dpi=(dpi, dpi))
                    size = output_io.tell()
                    
                    if size <= (ideal_kb + 1) * 1024:
                        break
                        
                    quality -= 2
                status = "optimized"
            
        output_io.seek(0)
        
        response = HttpResponse(output_io.read(), content_type='image/jpeg')
        response['Content-Disposition'] = 'attachment; filename="processed_image.jpg"'
        # Attach processed stats in headers so frontend can display them
        response['X-Processed-Width'] = str(width)
        response['X-Processed-Height'] = str(height)
        response['X-Processed-DPI'] = str(dpi)
        response['X-Processed-Size'] = str(size)
        response['X-Processed-Quality'] = str(quality)
        response['X-Compression-Status'] = status
        response['Access-Control-Expose-Headers'] = 'X-Processed-Width, X-Processed-Height, X-Processed-DPI, X-Processed-Size, X-Processed-Quality, X-Compression-Status, Content-Disposition'
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
