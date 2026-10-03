from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings

def home(request):
    html_path = os.path.join(settings.BASE_DIR.parent, 'uploader.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return HttpResponse(f.read())

def about(request):
    return render(request, 'about.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms(request):
    return render(request, 'terms.html')

def contact(request):
    return render(request, 'contact.html')

def disclaimer(request):
    return render(request, 'disclaimer.html')

def faq(request):
    return render(request, 'faq.html')

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /api/",
        "Allow: /",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

def sitemap_xml(request):
    base_url = request.build_absolute_uri('/')[:-1]
    urls = [
        "/",
        "/about",
        "/privacy-policy",
        "/terms-and-conditions",
        "/contact",
        "/disclaimer",
        "/faq"
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        xml.append('  <url>')
        xml.append(f'    <loc>{base_url}{url}</loc>')
        xml.append('    <changefreq>weekly</changefreq>')
        xml.append('    <priority>0.8</priority>')
        xml.append('  </url>')
    xml.append('</urlset>')
    return HttpResponse("\n".join(xml), content_type="application/xml")
