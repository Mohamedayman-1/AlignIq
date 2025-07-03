from threading import local

_thread_locals = local()

class UserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the user on the thread when a request comes in
        _thread_locals.user = getattr(request, 'user', None)
        response = self.get_response(request)
        # Clear the user so we don't have memory leaks
        _thread_locals.user = None
        return response

def get_current_user():
    return getattr(_thread_locals, 'user', None)
