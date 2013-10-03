
from django.views.generic import View
from django.contrib.auth.decorators import login_required

class LoginView(View):
    @classmethod
    def login_view(cls, *args, **kwargs):
        return login_required(cls.as_view(*args, **kwargs))
