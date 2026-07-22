from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("users:login")
        if not (request.user.is_superuser or request.user.is_admin_user):
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped
