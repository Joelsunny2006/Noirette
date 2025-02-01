from functools import wraps
from django.shortcuts import redirect

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('admin_sign_in')  # Ensure this matches your URL pattern
        return view_func(request, *args, **kwargs)
    return _wrapped_view
