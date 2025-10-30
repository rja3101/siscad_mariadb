from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.views import redirect_to_login

def role_required(allowed_names: list[str]):
    """
    Permite acceso si el usuario:
    - está autenticado y su user.role.name está en allowed_names, o
    - es superuser (atajo útil en desarrollo).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            role_name = getattr(getattr(user, "role", None), "name", None)
            if role_name in allowed_names:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No autorizado")
        return _wrapped
    return decorator
