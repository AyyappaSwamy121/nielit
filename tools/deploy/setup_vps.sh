#!/bin/bash
# Run this on your Ubuntu VPS as root or with sudo

APP_DIR="/var/www/my_django_app"

echo "Setting up VPS for Django Deployment..."

# 1. System updates and required packages
sudo apt update
sudo apt install -y python3-pip python3-venv nginx curl

# 2. Setup Application Directory
sudo mkdir -p $APP_DIR
# Copy your files to the APP_DIR. Assuming you are running this from your repo folder:
sudo cp -r . $APP_DIR
sudo chown -R www-data:www-data $APP_DIR

# 3. Setup Virtual Environment and Dependencies
cd $APP_DIR
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt

# 4. Django Setup (Migrations and Static Files)
sudo -u www-data venv/bin/python manage.py migrate
sudo -u www-data venv/bin/python manage.py collectstatic --noinput

# 5. Setup Gunicorn Systemd Service
sudo cp deploy/gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# 6. Setup Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/my_django_app
sudo ln -sf /etc/nginx/sites-available/my_django_app /etc/nginx/sites-enabled/
# Remove default nginx site if exists
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "Deployment setup complete! Your app should now be running on your server's IP address."
