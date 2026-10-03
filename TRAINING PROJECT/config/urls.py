from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from seo.sitemaps import StaticViewSitemap
from django.http import HttpResponse

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
    
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
