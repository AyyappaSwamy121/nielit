import fitz  # PyMuPDF
import io
from django.core.files.base import ContentFile

def compress_pdf(pdf_file, max_size_kb=2048):
    """
    Compresses a PDF file if it exceeds the maximum size limit using PyMuPDF.
    """
    pdf_bytes = pdf_file.read()
    if len(pdf_bytes) / 1024 <= max_size_kb:
        pdf_file.seek(0)
        return pdf_file
        
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    output = io.BytesIO()
    
    # Save with garbage collection and deflate for compression
    doc.save(output, garbage=4, deflate=True)
    output.seek(0)
    return ContentFile(output.read(), name=pdf_file.name)

def validate_pdf(pdf_file):
    pass

def merge_pdf(pdf_list):
    pass
