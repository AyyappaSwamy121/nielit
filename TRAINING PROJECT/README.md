# Enterprise Student Registration & Appreciation Portal

This project is a Django-based online registration portal where students can submit their applications securely.

## Prerequisites
- Python 3.13+
- Windows (Powershell/Command Prompt)

## Installation & Setup

1. **Activate the Virtual Environment**
   Open Powershell in the project root directory and run:
   ```powershell
   .\venv\Scripts\activate
   ```

2. **Install Dependencies**
   If not already installed, run:
   ```powershell
   pip install -r requirements.txt
   ```
   *(Note: For this project, we manually installed `django`, `pillow`, `PyMuPDF`, `openpyxl`, `pandas`, `qrcode`)*

3. **Database Setup**
   The project uses SQLite by default. Run the migrations to set up the database tables:
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create a Superuser**
   To access the Admin Dashboard, create a staff/admin user:
   ```powershell
   python manage.py createsuperuser
   ```

5. **Run the Development Server**
   Start the local server:
   ```powershell
   python manage.py runserver
   ```
   The public registration portal will be available at `http://127.0.0.1:8000/`.
   The dashboard export APIs will be under `http://127.0.0.1:8000/dashboard/`.

## Key Features

- **Public Registration without Login**: Students can fill the form and upload documents seamlessly.
- **Image & PDF Optimization**: Uses Pillow and PyMuPDF to aggressively optimize image sizes and PDFs while retaining visual quality.
- **Master Data Models**: State, District, Religion, Program, etc. are managed via Django Admin.
- **Exports**: Generate Excel sheets and ZIP archives containing all uploaded documents dynamically.

## Security Configurations Applied
- **CSRF Protection**: All forms and AJAX POST requests must include the CSRF token.
- **File Validation**: Image extensions (JPG, JPEG) and PDF boundaries are strictly checked.
- **Auth**: The dashboard paths require login authentication.
