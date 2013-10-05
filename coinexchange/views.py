
import traceback
import json

from django.http import HttpResponse, Http404
from django.views.generic import View
from django.contrib.auth.decorators import login_required



def catch_exceptions(fun):
    def new_fun(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except Exception as e:
            print "Exception caught: %s" % e
            print traceback.format_exc()
            raise e
    return new_fun

class LoginView(View):
    @classmethod
    def login_view(cls, *args, **kwargs):
        return catch_exceptions(login_required(cls.as_view(*args, **kwargs)))

class JsonResponse():
    def __init__(self, result, error=False):
        self.json_dict = {'result': result,
                          'error': error}
    def as_json(self):
        try:
            return json.dumps(self.json_dict)
        except Exception as e:
            print e
            raise e

    def http_response(self):
        resp = HttpResponse(self.as_json())
        resp['Content-Type'] = "application/json"
        return resp
