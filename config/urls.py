from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from seo.sitemaps import StaticViewSitemap
from django.http import HttpResponse

from tools_portal import views as tools_views

sitemaps = {
    'static': StaticViewSitemap,
}

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /dashboard/",
        "Disallow: /api/",
        "Disallow: /preview/",
        "Disallow: /success/",
        "Disallow: /media/",
        "Disallow: /exports/",
        "Disallow: /downloads/",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', admin.site.login, name='admin_panel_login'),
    path('dashboard/', include('dashboard.urls')),
    path('masterdata/', include('masterdata.urls')),
    path('', include('registrations.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),

    # Integrated converter (tools/): UI at /tools/, processing API and its own
    # secondary pages served on this same port.
    path('tools/', include('tools_portal.urls')),
    path('api/process-image/', tools_views.process_image, name='tools_process_image'),
    path('favicon.ico', tools_views.favicon_ico, name='tools_favicon'),
    path('about', tools_views.about, name='tools_about'),
    path('privacy-policy', tools_views.privacy_policy, name='tools_privacy_policy'),
    path('terms-and-conditions', tools_views.terms, name='tools_terms'),
    path('contact', tools_views.contact, name='tools_contact'),
    path('disclaimer', tools_views.disclaimer, name='tools_disclaimer'),
    path('faq', tools_views.faq, name='tools_faq'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
