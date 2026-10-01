from django.contrib.auth import logout
from django.http import JsonResponse


class ActiveUserRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_active:
            logout(request)
            if request.path.startswith("/api/"):
                return JsonResponse({"detail": "Los datos ingresados son incorrectos o la cuenta está inhabilitada."}, status=403)
        return self.get_response(request)
