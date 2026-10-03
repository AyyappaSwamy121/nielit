import io
import os
import logging
from PIL import Image, ImageOps
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

PASSPORT_PHOTO = 'passport_photo'
SIGNATURE = 'signature'
LEFT_THUMB = 'left_thumb'

def process_and_optimize_image(image_field, doc_type):
    dt_norm = doc_type.lower().replace(' ', '_')
    is_passport = 'passport' in dt_norm
    is_signature = 'signature' in dt_norm
    is_thumb = 'thumb' in dt_norm

    target_dpi = (300, 300)
    min_kb, max_kb = 5, 500
    resize_mode = 'fit'

    if is_passport:
        canon_doc_type = PASSPORT_PHOTO
        target_width, target_height = 132, 170
        target_dpi = (300, 300)
        min_kb, max_kb = 5, 50
        processing_policy = 'passport_fixed'
    elif is_signature:
        canon_doc_type = SIGNATURE
        target_width, target_height = 170, 132
        target_dpi = (200, 200)
        min_kb, max_kb = 5, 20
        processing_policy = 'signature_fixed'
    elif is_thumb:
        canon_doc_type = LEFT_THUMB
        target_width, target_height = 170, 132
        target_dpi = (200, 200)
        min_kb, max_kb = 5, 20
        processing_policy = 'thumb_fixed'
    else:
        canon_doc_type = dt_norm
        target_dpi = (300, 300)
        processing_policy = 'document_preserve'

    img = Image.open(image_field)
    original_file_size = image_field.size

    img = ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode in ("RGBA", "LA"):
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    optimized_bytes = None
    best_quality = None
    v_width, v_height = img.size
    
    if processing_policy == 'passport_fixed':
        clean_img = ImageOps.fit(img, (target_width, target_height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        v_width, v_height = clean_img.size
        for q in range(95, 9, -1):
            temp_out = io.BytesIO()
            clean_img.save(temp_out, format='JPEG', quality=q, optimize=True, dpi=target_dpi, subsampling=0)
            size_kb = temp_out.tell() / 1024.0
            if size_kb <= max_kb:
                best_quality = q
                optimized_bytes = temp_out.getvalue()
                break
        if not optimized_bytes:
            temp_out = io.BytesIO()
            clean_img.save(temp_out, format='JPEG', quality=10, optimize=True, dpi=target_dpi, subsampling=0)
            optimized_bytes = temp_out.getvalue()
            best_quality = 10
            
    elif processing_policy in ('signature_fixed', 'thumb_fixed'):
        img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        clean_img = Image.new('RGB', (target_width, target_height), (255, 255, 255))
        offset = ((target_width - img.width) // 2, (target_height - img.height) // 2)
        clean_img.paste(img, offset)
        v_width, v_height = clean_img.size
        for q in range(95, 9, -1):
            temp_out = io.BytesIO()
            clean_img.save(temp_out, format='JPEG', quality=q, optimize=True, dpi=target_dpi, subsampling=0)
            size_kb = temp_out.tell() / 1024.0
            if size_kb <= max_kb:
                best_quality = q
                optimized_bytes = temp_out.getvalue()
                break
        if not optimized_bytes:
            temp_out = io.BytesIO()
            clean_img.save(temp_out, format='JPEG', quality=10, optimize=True, dpi=target_dpi, subsampling=0)
            optimized_bytes = temp_out.getvalue()
            best_quality = 10
            
    elif processing_policy == 'document_preserve':
        max_dimension = 2560
        clean_img = img.copy()
        if max(clean_img.size) > max_dimension:
            clean_img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        v_width, v_height = clean_img.size
        
        # We don't want to over-compress if there's no strict kb constraint
        # Save at high quality to standardize output format to JPEG
        best_quality = 95
        temp_out = io.BytesIO()
        clean_img.save(temp_out, format='JPEG', quality=best_quality, optimize=True, dpi=target_dpi, subsampling=0)
        optimized_bytes = temp_out.getvalue()

    optimized_file_size = len(optimized_bytes)
    compression_percent = ((original_file_size - optimized_file_size) / original_file_size) * 100 if original_file_size > 0 else 0
    compression_percent = max(0, compression_percent)

    validation_status = 'PASS'
    if processing_policy in ('passport_fixed', 'signature_fixed', 'thumb_fixed'):
        v_size_kb = optimized_file_size / 1024.0
        if v_width != target_width or v_height != target_height:
            validation_status = 'FAIL'
        if not (min_kb <= v_size_kb <= max_kb):
            validation_status = 'FAIL'

    image_field.seek(0)
    original_file_content = ContentFile(image_field.read(), name='original.jpg')
    optimized_file_content = ContentFile(optimized_bytes, name='optimized.jpg')

    return {
        'original_file': original_file_content,
        'optimized_file': optimized_file_content,
        'original_file_size': original_file_size,
        'optimized_file_size': optimized_file_size,
        'image_width': v_width,
        'image_height': v_height,
        'mime_type': 'image/jpeg',
        'compression_percentage': round(compression_percent, 2),
        'jpeg_quality': best_quality,
        'validation_status': validation_status,
        'processing_policy': processing_policy
    }
