"""Views that expose the existing converter (tools/) inside the Django project.

The converter's own frontend (uploader.html), secondary pages and processing API
are served through the main project on port 8000. Its code is reused, not copied.
"""

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

# Reuse the existing converter's processing view directly (no duplication).
from api import views as converter_api

CONVERTER_ENGINE = 'converter'


def _read_tools_file(relpath, binary=False):
    path = settings.BASE_DIR / 'tools' / relpath
    if binary:
        with open(path, 'rb') as f:
            return f.read()
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def tools_home(request):
    """Serves the existing converter UI (uploader.html) at /tools/.

    Rendered through Django's template engine so the header can use named URL
    routing ({% url %}) for the Home/Tools navigation.
    """
    return HttpResponse(
        render_to_string('uploader.html', request=request, using=CONVERTER_ENGINE)
    )


def favicon_ico(request):
    return HttpResponse(
        _read_tools_file('favicon.ico', binary=True),
        content_type='image/x-icon',
    )


@csrf_exempt
def process_image(request):
    """Existing converter processing endpoint (/api/process-image/).

    The converter intentionally exempts this endpoint from CSRF because it
    processes binary file uploads sent with fetch()/FormData (no HTML form, no
    cookie-bound session). The exemption is preserved when reusing it here.
    """
    return converter_api.process_image(request)


def _render_converter_page(request, template_name):
    return render_to_string(template_name, request=request, using=CONVERTER_ENGINE)


def about(request):
    return HttpResponse(_render_converter_page(request, 'about.html'))


def privacy_policy(request):
    return HttpResponse(_render_converter_page(request, 'privacy_policy.html'))


def terms(request):
    return HttpResponse(_render_converter_page(request, 'terms.html'))


def contact(request):
    return HttpResponse(_render_converter_page(request, 'contact.html'))


def disclaimer(request):
    return HttpResponse(_render_converter_page(request, 'disclaimer.html'))


def faq(request):
    return HttpResponse(_render_converter_page(request, 'faq.html'))
