import qrcode
import io
from django.core.files.base import ContentFile

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
    output = io.BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return ContentFile(output.read(), name='qr_code.png')
