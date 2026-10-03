import io
import fitz  # PyMuPDF
import qrcode
from PIL import Image
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from xhtml2pdf import pisa
from django.conf import settings
import os
import base64

def generate_qr_code(application):
    """
    Generates a QR code containing application details and returns it as a base64 encoded string
    to embed directly in the HTML template for xhtml2pdf.
    """
    data = f"App No: {application.application_number}\nName: {application.full_name}\nDate: {application.submission_date.strftime('%Y-%m-%d')}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def generate_acknowledgement_files(application):
    """
    Generates A4 PDF, high-res PNG, and high-res JPG of the acknowledgement card.
    Saves them directly to the StudentApplication instance.
    """
    
    # 1. Prepare Context for PDF template
    qr_base64 = generate_qr_code(application)
    
    # Get the passport photo path to embed in PDF
    passport_doc = application.documents.filter(doc_type='Passport_Photo').first()
    passport_path = None
    if passport_doc and passport_doc.compressed_file:
        passport_path = passport_doc.compressed_file.path
        
    context = {
        'app': application,
        'qr_code': qr_base64,
        'passport_path': passport_path,
        'STATIC_ROOT': settings.STATIC_ROOT,
        'MEDIA_ROOT': settings.MEDIA_ROOT,
    }
    
    html_string = render_to_string('registration/acknowledgement_template.html', context)
    
    # 2. Generate PDF
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)
    if pisa_status.err:
        raise Exception(f"PDF generation failed: {pisa_status.err}")
        
    pdf_bytes = pdf_buffer.getvalue()
    
    # 3. Generate PNG and JPG using PyMuPDF (fitz) at 300 DPI
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = pdf_document[0]
    
    # Zoom factor for 300 DPI (72 DPI is default, so 300/72 = ~4.16)
    zoom = 300 / 72
    matrix = fitz.Matrix(zoom, zoom)
    
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    
    png_bytes = pix.tobytes("png")
    
    # To get JPG, we use Pillow because fitz direct jpeg might have issues with some color spaces
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    jpg_buffer = io.BytesIO()
    img.save(jpg_buffer, format="JPEG", quality=95)
    jpg_bytes = jpg_buffer.getvalue()
    
    # 4. Save files to Model
    # Prefix filename to ensure uniqueness isn't an issue, Django handles appending _1
    app_no = application.application_number
    
    application.acknowledgement_pdf.save(f"{app_no}_Acknowledgement.pdf", ContentFile(pdf_bytes), save=False)
    application.acknowledgement_png.save(f"{app_no}_Acknowledgement.png", ContentFile(png_bytes), save=False)
    application.acknowledgement_jpg.save(f"{app_no}_Acknowledgement.jpg", ContentFile(jpg_bytes), save=False)
    
    application.save()
