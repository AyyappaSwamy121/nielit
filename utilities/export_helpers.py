import io
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import qrcode

def generate_student_details_excel(app):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Details"
    
    # Header
    fields = [
        "Application Number", "Full Name", "Father Name", "Mother Name", "Date of Birth",
        "Gender", "Religion", "Marital Status", "Community", "Nationality",
        "Physically Handicapped", "Annual Income",
        "Ex-Service Man", "Occupation",
        "Aadhaar Number", "Mobile Number", "Alternative Mobile", "Email", 
        "Communication Address", "Country", "State", "District", "Pincode",
        "Institution", "Hall Ticket Number", "Registration Number", "NIELIT Registration Number", "ABC ID",
        "Qualification", "Year of Passing", "Program", "Batch Code", "Submission Date", 
        "Status", "Verification Status"
    ]
    ws.append(fields)
    
    # Data
    data = [
        app.application_number, app.full_name, app.father_name, app.mother_name, 
        app.dob.strftime('%Y-%m-%d') if app.dob else "",
        app.gender, app.religion.name if app.religion else "", 
        app.marital_status.name if app.marital_status else "",
        app.community.name if app.community else "", 
        app.nationality,
        app.physically_handicapped, app.annual_income,
        app.ex_serviceman.name if app.ex_serviceman else "",
        app.occupation.name if app.occupation else "", 
        app.aadhaar_number, app.mobile_number, app.alternative_mobile, app.email,
        app.communication_address, app.country.name if app.country else "", 
        app.state.name if app.state else "", app.district.name if app.district else "", 
        app.pincode, app.institution, app.hall_ticket_number, app.registration_number, 
        app.nielit_registration_number, app.abc_id, app.qualification.name if app.qualification else "", 
        app.year_of_passing or "", 
        app.program_opting.name if app.program_opting else "",
        app.batch_code,
        app.submission_date.strftime('%Y-%m-%d %H:%M:%S') if app.submission_date else "",
        app.status.name if app.status else "",
        app.verification_status.name if app.verification_status else ""
    ]
    ws.append(data)
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()

def generate_student_information_pdf(app):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(1*inch, height - 1*inch, "Student Information")
    
    p.setFont("Helvetica", 12)
    y = height - 1.5*inch
    
    # Format details
    details = [
        f"Application Number: {app.application_number}",
        f"Name: {app.full_name}",
        f"Father's Name: {app.father_name}",
        f"Mobile: {app.mobile_number}",
        f"Email: {app.email}",
        f"Aadhaar: ********{app.aadhaar_number[-4:]}" if app.aadhaar_number else "Aadhaar: -",
        f"ABC ID: {app.abc_id}",
        f"Program: {app.program_opting.name if app.program_opting else '-'}",
        f"Qualification: {app.qualification.name if app.qualification else '-'}",
        f"Institution: {app.institution}",
        f"State: {app.state.name if app.state else '-'}",
        f"District: {app.district.name if app.district else '-'}",
        f"Submission Date: {app.submission_date.strftime('%Y-%m-%d') if app.submission_date else '-'}",
        f"Status: {app.status.name if app.status else '-'}",
    ]
    
    for text in details:
        p.drawString(1*inch, y, text)
        y -= 0.3*inch
        
    # Generate QR Code
    qr = qrcode.QRCode(version=1, box_size=4, border=4)
    qr.add_data(f"App No: {app.application_number}\nName: {app.full_name}\nAadhaar: ********{app.aadhaar_number[-4:] if app.aadhaar_number else '-'}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    
    qr_reader = ImageReader(qr_buffer)
    p.drawImage(qr_reader, width - 3*inch, height - 3*inch, width=1.5*inch, height=1.5*inch)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.read()
