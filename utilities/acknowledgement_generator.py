import io
import qrcode
from PIL import Image, ImageDraw, ImageFont
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.conf import settings
from dashboard.models import PlatformSetting
import os
import base64

# Optional dependency: pisa (xhtml2pdf). If unavailable, fall back to
# generating placeholder acknowledgment images so final_submit doesn't fail.
try:
    from xhtml2pdf import pisa
    HAVE_PISA = True
except Exception:
    HAVE_PISA = False

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
        'platform_settings': PlatformSetting.get_active(),
        'STATIC_ROOT': settings.STATIC_ROOT,
        'MEDIA_ROOT': settings.MEDIA_ROOT,
    }
    
    html_string = render_to_string('registration/acknowledgement_template.html', context)
    
    app_no = application.application_number

    if HAVE_PISA:
        # 2. Generate PDF
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)
        if pisa_status.err:
            raise Exception(f"PDF generation failed: {pisa_status.err}")
        pdf_bytes = pdf_buffer.getvalue()

        # 3. Generate PNG and JPG using PyMuPDF if available
        try:
            import fitz  # PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = pdf_document[0]
            zoom = 300 / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(png_bytes))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            jpg_buffer = io.BytesIO()
            img.save(jpg_buffer, format="JPEG", quality=95)
            jpg_bytes = jpg_buffer.getvalue()
        except Exception:
            # Fall back to simple placeholder image bytes
            png_buf = io.BytesIO()
            img = Image.new('RGB', (600, 400), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            d.text((20, 180), f"Acknowledgement: {app_no}", fill=(0, 0, 0))
            img.save(png_buf, format='PNG')
            png_bytes = png_buf.getvalue()
            jpg_buf = io.BytesIO()
            img.save(jpg_buf, format='JPEG', quality=85)
            jpg_bytes = jpg_buf.getvalue()

        # Save generated files
        try:
            application.acknowledgement_pdf.save(f"{app_no}_Acknowledgement.pdf", ContentFile(pdf_bytes), save=False)
        except Exception:
            # If PDF save fails, skip it but continue
            pass
        application.acknowledgement_png.save(f"{app_no}_Acknowledgement.png", ContentFile(png_bytes), save=False)
        application.acknowledgement_jpg.save(f"{app_no}_Acknowledgement.jpg", ContentFile(jpg_bytes), save=False)
        application.save()
    else:
        # xhtml2pdf/pisa not available; generate placeholder PNG/JPG and skip PDF
        png_buf = io.BytesIO()
        img = Image.new('RGB', (600, 400), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((20, 180), f"Acknowledgement: {app_no}", fill=(0, 0, 0))
        img.save(png_buf, format='PNG')
        png_bytes = png_buf.getvalue()
        jpg_buf = io.BytesIO()
        img.save(jpg_buf, format='JPEG', quality=85)
        jpg_bytes = jpg_buf.getvalue()

        application.acknowledgement_png.save(f"{app_no}_Acknowledgement.png", ContentFile(png_bytes), save=False)
        application.acknowledgement_jpg.save(f"{app_no}_Acknowledgement.jpg", ContentFile(jpg_bytes), save=False)
        application.save()
