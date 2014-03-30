
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
from coinexchange.main import lib

@login_required
def authorize(request):
    args = ['response_type=code',
            'client_id=%s' % COINBASE_API.get('client_id'),
            'redirect_uri=%s' % COINBASE_API.get('redirect_uri'),
            'scope=%s' % coinbase.COINBASE_PERMS,
            ]
    merchant = request.user.get_profile()
    meta_params = coinbase.get_merchant_meta_params(merchant)
    for k in meta_params.keys():
        args.append("%s=%s" % (k,meta_params[k]))
    target = "https://coinbase.com/oauth/authorize?%s" % ('&'.join(args))
    return HttpResponseRedirect(target)

@login_required
def redirect(request):
    profile = request.user.get_profile()
    creds = ApiCreds.load_by_merchant(profile)
    if 'code' in request.GET:
        print request.GET['code']
        creds.code = request.GET['code']
        creds.save()
        print coinbase.get_access_token(creds, creds.code)
    else:
        err = request.GET['error']
        err_desc = request.GET['error_description']
        error_info = "Coinbase Authorization Failed: %s - %s" % (err, err_desc)
        lib.StatusMessages.add_error(request, error_info)
    return HttpResponseRedirect(reverse('account_settings'))
