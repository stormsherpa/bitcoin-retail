
import datetime
import decimal

from django.http import HttpResponse, Http404
from django.template import loader
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.generic import View

from coinexchange.views import LoginView
from coinexchange.main.forms import SignupForm, WithdrawlRequestForm, SellOfferForm
from coinexchange.main.lib import CoinExchangeContext, StatusMessages
from coinexchange.btc.models import CoinTxnLog, WithdrawlRequest
from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc import clientlib

def signup(request):
    signup_form = SignupForm()
    if request.method == "POST":
        signup_form = SignupForm(request.POST)
        username = request.POST.get('username', None)
        email = request.POST.get('email', None)
        password = request.POST.get('password', None)
        if not username or not email or not password:
            return redirect('auth_login')
        if password == request.POST.get('password2', None):
            user = User.objects.create_user(username, email, password)
            user2 = authenticate(username = username, password=password)
            login(request, user2)
            return redirect('account_home')
        else:
            pass
    t = loader.get_template("coinexchange/signup.html")
    c = CoinExchangeContext(request, {'form': signup_form})
    return HttpResponse(t.render(c))

@login_required
def home(request):
    profile = request.user.get_profile()
    coin_txn = profile.coin_txn.order_by('tx_timestamp')
    sell_offers = [SellOfferForm(instance=x) for x in profile.sell_offers.order_by('price')]
    print sell_offers
    t = loader.get_template("coinexchange/account/main.html")
    c = CoinExchangeContext(request, {'coin_txn': coin_txn,
                                      'withdrawl_form': WithdrawlRequestForm(),
                                      'sell_form': SellOfferForm(),
                                      'sell_offers': sell_offers})
    return HttpResponse(t.render(c))

@login_required
def settings(request):
    t = loader.get_template("coinexchange/account/settings.html")
    c = CoinExchangeContext(request, {})
    return HttpResponse(t.render(c))
