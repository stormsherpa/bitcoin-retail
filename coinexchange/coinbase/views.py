
import json
import decimal

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import loader
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.generic import View

from coinexchange.settings import COINBASE_API
from coinexchange import coinbase
from coinexchange.coinbase.models import ApiCreds

@login_required
def authorize(request):
    args = ['response_type=code',
            'client_id=%s' % COINBASE_API.get('client_id'),
            'redirect_uri=%s' % COINBASE_API.get('redirect_uri'),
            'scope=%s' % coinbase.COINBASE_PERMS,
            ]
    target = "https://coinbase.com/oauth/authorize?%s" % ('&'.join(args))
    return HttpResponseRedirect(target)

@login_required
def redirect(request):
    profile = request.user.get_profile()
    creds = ApiCreds.load_by_merchant(profile)
    print request.GET['code']
    creds.code = request.GET['code']
    creds.save()
    print coinbase.get_access_token(creds, creds.code)
    target = "/account/pos"
    return HttpResponseRedirect(target)
