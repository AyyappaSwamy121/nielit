from dashboard.models import PlatformSetting


def platform_settings(request):
    return {
        'platform_settings': PlatformSetting.get_active(),
    }
