
import datetime
import decimal
import json
import traceback
import hashlib

from django.http import HttpResponse, Http404
from django.template import loader
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.generic import View

from django.conf import settings

from coinexchange.views import LoginView, JsonResponse
from coinexchange.main.forms import SignupForm, WithdrawlRequestForm, SellOfferForm
from coinexchange.main.lib import CoinExchangeContext, StatusMessages
from coinexchange.btc.models import CoinTxnLog, WithdrawlRequest, SellOffer
from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc import clientlib
from coinexchange.btc.pos.models import SalesTransaction


@login_required
def root(request):
    response = {'endpoints':
                [reverse('api_withdrawl')]}
    http_response = HttpResponse(json.dumps(response))
    http_response['Content-Type'] = 'application/json'
    return http_response

def js(request):
    t = loader.get_template("coinexchange/account/api.js");
    c = CoinExchangeContext(request, {})
    http_response = HttpResponse(t.render(c))
    http_response['Content-Type'] = 'application/javascript'
    return http_response

def state(request):
    if request.user.is_authenticated():
        profile = request.user.get_profile()
        session_status = {
                          'balance': "%0.8f" % clientlib.get_user_balance(profile),
                          'address': clientlib.get_user_address(profile),
                          }
    else:
        session_status = dict()
    http_response = HttpResponse(json.dumps(session_status, indent=2)+"\n")
    http_response['Content-Type'] = 'application/json'
    return http_response

@login_required
def newsale(request):
    profile = request.user.get_profile()
    address = clientlib.get_user_address(profile)
    currency = "USD"
    exchange_rate = 795
    fiat_amount = decimal.Decimal(request.POST['amount'])
    btc_amount = fiat_amount/exchange_rate
    sale = SalesTransaction(merchant=profile,
                            reference=request.POST['reference'],
                            amount=fiat_amount,
                            currency=currency,
                            currency_btc_exchange_rate=exchange_rate,
                            btc_amount=btc_amount,
                            btc_address=address)
    sale.save()
    response = {
                'sale_id': sale.id,
                'address': address,
                'currency': 'USD',
                'fiat_amount': "%0.2f" % fiat_amount,
                'btc_amount': "%0.8f" % btc_amount,
                }
    http_response = HttpResponse(json.dumps(response)+"\n")
    http_response['Content-Type'] = 'application/json'
    return http_response

@login_required
def xmpp_creds(request):
    username = "account-id-%s" % request.user.id
    domain = getattr(settings, 'XMPP_DOMAIN', 'stormsherpa.com')
    server = getattr(settings, 'XMPP_BOSH_URL', 'http://stormsherpa.com:5280/http-bind')
    password_psk = getattr(settings, 'XMPP_AUTH_PRESHARED_KEY', 'coinExchange')
    passwd_in_str = "%s@%s:%s" % (username, domain, password_psk)
    passwd_str = hashlib.md5(passwd_in_str).hexdigest()
    creds = {'username': "%s@%s" % (username, domain),
             'password': passwd_str,
             'bosh_url': server}
    http_response = HttpResponse(json.dumps(creds, indent=2))
    http_response['Content-Type'] = 'application/javascript'
    return http_response

class WithdrawlView(LoginView):

    def post(self, request):
        profile = request.user.get_profile()
        balance = clientlib.get_user_balance(profile)
        data = json.loads(request.raw_post_data)
        print data
        withdrawl_form = WithdrawlRequestForm(data)
        if not data.get('amount'):
            msg = "No withdrawl amount entered."
            return JsonResponse(msg, error=True).http_response()
        amount = decimal.Decimal(data['amount'])
        if withdrawl_form.is_valid() and amount <= balance:
            withdrawl = withdrawl_form.save(commit=False)
            withdrawl.user = profile
            withdrawl.status = "not_requested"
            withdrawl.save()
            btc_client = BitcoindClient.get_instance()
            withdrawl_result = btc_client.user_withdrawl(withdrawl)
            withdrawl.txid = withdrawl_result.get('txid', 'No txid set')
            withdrawl.status = withdrawl_result.get('result', "no_status")
            withdrawl.save()
            return JsonResponse(withdrawl_result['result'], error=withdrawl_result['error']).http_response()
        msg = "Some fields had errors: %s" % ','.join(withdrawl_form.errors)
        return JsonResponse(msg, error=True).http_response()

