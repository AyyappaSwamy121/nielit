import io
import os
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image


# ── helpers ──────────────────────────────────────────────────────────────────

def _insert_com_segments(jpeg_bytes: bytes, total_pad: int) -> bytes:
    """
    Insert one or more valid JPEG COM (0xFFFE) segments carrying `total_pad`
    null bytes, immediately before the End‑Of‑Image marker (0xFFD9).

    Each COM segment payload is capped at 65533 bytes
    (the JPEG limit is 65535 for the length field, which includes its own
    2 bytes, so max payload = 65535 - 2 = 65533).

    The EOI marker is NOT moved; we split body / eoi first.
    """
    # Make sure the JPEG ends with EOI
    if jpeg_bytes[-2:] == b'\xFF\xD9':
        body = jpeg_bytes[:-2]
        eoi  = b'\xFF\xD9'
    else:
        # Defensive: treat entire buffer as body, append EOI later
        body = jpeg_bytes
        eoi  = b'\xFF\xD9'

    MAX_PAYLOAD = 65533  # max bytes we can put in one COM segment
    remaining   = total_pad
    segments    = b''

    while remaining > 0:
        chunk_size  = min(remaining, MAX_PAYLOAD)
        # Length field = chunk_size + 2 (includes the 2 length bytes itself)
        seg_length  = (chunk_size + 2).to_bytes(2, 'big')
        segments   += b'\xFF\xFE' + seg_length + b'\x00' * chunk_size
        remaining  -= chunk_size

    return body + segments + eoi


def _validate_jpeg(buf: bytes, expected_w: int, expected_h: int,
                   expected_dpi: int, min_bytes: int, max_bytes: int):
    """
    Reload buf with Pillow and verify dimensions, DPI, and size.
    Raises ValueError with a descriptive message on any failure.
    """
    try:
        check_io = io.BytesIO(buf)
        check_img = Image.open(check_io)
        check_img.load()
    except Exception as e:
        raise ValueError(f"Cannot reload generated JPEG: {e}")

    if check_img.format != 'JPEG':
        raise ValueError(f"Output is {check_img.format}, expected JPEG")

    w, h = check_img.size
    if w != expected_w or h != expected_h:
        raise ValueError(
            f"Dimension mismatch: got {w}×{h}, expected {expected_w}×{expected_h}"
        )

    dpi_info = check_img.info.get('dpi')
    if dpi_info:
        rdpi = round(dpi_info[0])
        if rdpi != expected_dpi:
            raise ValueError(f"DPI mismatch: got {rdpi}, expected {expected_dpi}")

    size = len(buf)
    if not (min_bytes <= size <= max_bytes):
        raise ValueError(
            f"Size {size} bytes is outside the allowed range "
            f"[{min_bytes}, {max_bytes}]"
        )


# ── view ─────────────────────────────────────────────────────────────────────

@csrf_exempt
def process_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        width        = int(request.POST.get('width',  132))
        height       = int(request.POST.get('height', 170))
        min_size_kb  = int(request.POST.get('minSize', 5))
        max_size_kb  = int(request.POST.get('maxSize', 20))
        dpi          = int(request.POST.get('dpi', 270))
        resize_algo  = request.POST.get('resizeAlgorithm', 'Lanczos3')

        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'error': 'No image provided'}, status=400)

        # ── 1. Open & orient ─────────────────────────────────────────────────
        img = Image.open(image_file)

        # Apply EXIF orientation if present
        try:
            exif = img._getexif()
            if exif:
                orientation = exif.get(274)  # 274 = Orientation tag
                ORIENT_MAP = {
                    2: Image.FLIP_LEFT_RIGHT,
                    3: Image.ROTATE_180,
                    4: Image.FLIP_TOP_BOTTOM,
                    5: (Image.FLIP_LEFT_RIGHT, Image.ROTATE_90),
                    6: Image.ROTATE_270,
                    7: (Image.FLIP_LEFT_RIGHT, Image.ROTATE_270),
                    8: Image.ROTATE_90,
                }
                op = ORIENT_MAP.get(orientation)
                if op:
                    if isinstance(op, tuple):
                        img = img.transpose(op[0]).transpose(op[1])
                    else:
                        img = img.transpose(op)
        except Exception:
            pass  # No EXIF or unreadable – continue

        # ── 2. Convert to RGB (handle transparency) ──────────────────────────
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # ── 3. Resize ────────────────────────────────────────────────────────
        if resize_algo == 'INTER_AREA':
            import cv2
            import numpy as np
            arr     = np.array(img)[:, :, ::-1]  # RGB → BGR
            resized = cv2.resize(arr, (width, height), interpolation=cv2.INTER_AREA)
            img     = Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
        elif resize_algo == 'Bicubic Sharper':
            img = img.resize((width, height), resample=Image.Resampling.BICUBIC)
        else:
            img = img.resize((width, height), resample=Image.Resampling.LANCZOS)

        # ── 4. Byte limits ───────────────────────────────────────────────────
        min_bytes    = min_size_kb * 1024          # e.g. 5120
        max_bytes    = max_size_kb * 1024          # e.g. 20480
        # Target for padding: aim for the midpoint of the allowed range
        # (capped at max_bytes).  For a 5–20 KB range this gives ~9 KB.
        TARGET_BYTES = min(max_bytes, max(min_bytes, (min_bytes + max_bytes) // 2))

        quality   = 100
        status    = 'optimized'

        # ── 5. Initial encode at quality 100 ─────────────────────────────────
        output_io = io.BytesIO()
        img.save(output_io, format='JPEG', quality=quality,
                 dpi=(dpi, dpi), subsampling=0, optimize=False)
        size = output_io.tell()

        # ── 6a. Too big → compress ────────────────────────────────────────────
        if size > max_bytes:
            status = 'unknown'
            for q in range(95, 5, -5):
                temp_io = io.BytesIO()
                img.save(temp_io, format='JPEG', quality=q,
                         dpi=(dpi, dpi), optimize=True)
                temp_size = temp_io.tell()
                if temp_size <= max_bytes:
                    output_io = temp_io
                    size      = temp_size
                    quality   = q
                    status    = 'optimized' if temp_size >= min_bytes else 'below_minimum'
                    break
            else:
                status = 'exceeds_maximum'

        # ── 6b. Too small → pad with COM segment(s) ──────────────────────────
        elif size < min_bytes:
            padding_needed = TARGET_BYTES - size
            if padding_needed < 0:
                padding_needed = min_bytes - size  # safety fallback

            jpeg_bytes = output_io.getvalue()
            new_jpeg   = _insert_com_segments(jpeg_bytes, padding_needed)
            size       = len(new_jpeg)
            output_io  = io.BytesIO(new_jpeg)
            status     = 'optimized'

        # ── 7. Back‑validate ──────────────────────────────────────────────────
        final_bytes = output_io.getvalue()
        try:
            _validate_jpeg(final_bytes, width, height, dpi, min_bytes, max_bytes)
        except ValueError as ve:
            # Validation failed – report clearly
            return JsonResponse({'error': str(ve), 'status': 'invalid_output'}, status=422)

        # ── 8. Return response ────────────────────────────────────────────────
        response = HttpResponse(final_bytes, content_type='image/jpeg')
        response['Content-Disposition'] = 'attachment; filename="processed_image.jpg"'
        response['X-Processed-Width']   = str(width)
        response['X-Processed-Height']  = str(height)
        response['X-Processed-DPI']     = str(dpi)
        response['X-Processed-Size']    = str(size)
        response['X-Processed-Quality'] = str(quality)
        response['X-Compression-Status'] = status
        response['Access-Control-Expose-Headers'] = (
            'X-Processed-Width, X-Processed-Height, X-Processed-DPI, '
            'X-Processed-Size, X-Processed-Quality, X-Compression-Status, '
            'Content-Disposition'
        )
        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
