import os
import sys
import django
from django.template.loader import render_to_string

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'django_backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.test import RequestFactory
rf = RequestFactory()
request = rf.get('/')

html = render_to_string('home.html', request=request)

with open('uploader.html', 'w', encoding='utf-8') as f:
    f.write(html)
