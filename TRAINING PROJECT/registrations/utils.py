import os
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
from django.core.files.base import ContentFile
import qrcode

def compress_image(image, max_size_kb, min_size_kb=5):
    """
    Compresses an image to be within the specified size range without losing too much visual quality.
    Strips EXIF data by creating a new image.
    """
    img = Image.open(image)
    
    # Strip EXIF and convert to RGB (removes transparency if any, good for JPG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    else:
        # Create a copy without metadata
        data = list(img.getdata())
        image_without_exif = Image.new(img.mode, img.size)
        image_without_exif.putdata(data)
        img = image_without_exif
        
    output = BytesIO()
    quality = 95
    
    # Initial save
    img.save(output, format='JPEG', quality=quality, optimize=True)
    
    # If the image is already smaller than the max size, just return it
    if output.tell() / 1024 <= max_size_kb:
        output.seek(0)
        return ContentFile(output.read(), name=image.name)
        
    # Binary search for the right quality
    min_q = 10
    max_q = 95
    best_output = output
    
    while min_q <= max_q:
        quality = (min_q + max_q) // 2
        temp_output = BytesIO()
        img.save(temp_output, format='JPEG', quality=quality, optimize=True)
        size_kb = temp_output.tell() / 1024
        
        if size_kb <= max_size_kb:
            best_output = temp_output
            if size_kb >= min_size_kb:
                break
            min_q = quality + 1
        else:
            max_q = quality - 1
            
    best_output.seek(0)
    return ContentFile(best_output.read(), name=image.name)

def compress_pdf(pdf_file, max_size_kb=2048):
    """
    Optimizes a PDF using PyMuPDF if it exceeds the max size.
    """
    pdf_bytes = pdf_file.read()
    if len(pdf_bytes) / 1024 <= max_size_kb:
        pdf_file.seek(0)
        return pdf_file
        
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    output = BytesIO()
    # Save with garbage collection and deflate to reduce size
    doc.save(output, garbage=4, deflate=True)
    output.seek(0)
    return ContentFile(output.read(), name=pdf_file.name)

def generate_qr_code(data):
    """
    Generates a QR code image for the given data (e.g., application number).
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return ContentFile(output.read(), name='qr_code.png')
