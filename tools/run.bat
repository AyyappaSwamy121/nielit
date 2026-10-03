@echo off
echo Starting Django Backend Server...
start cmd /k "venv\Scripts\activate.bat & python manage.py runserver"

echo Backend server started on port 8000.
echo Opening the frontend in your browser...
start http://127.0.0.1:8000/
