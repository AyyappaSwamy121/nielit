class XRobotsTagMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if the path is in the protected list
        path = request.path_info
        protected_prefixes = ['/api/', '/preview/', '/success/', '/dashboard/', '/admin/', '/media/', '/exports/', '/downloads/']
        
        if any(path.startswith(prefix) for prefix in protected_prefixes):
            response['X-Robots-Tag'] = 'noindex, nofollow, noarchive, nosnippet, noimageindex'
            
        return response
