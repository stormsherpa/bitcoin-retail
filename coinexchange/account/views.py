
import datetime
import pika
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
    t = loader.get_template("coinexchange/account/balance.html")
    c = CoinExchangeContext(request, {'coin_txn': coin_txn})
    return HttpResponse(t.render(c))

@login_required
def settings(request):
    t = loader.get_template("coinexchange/account/edit.html")
    c = CoinExchangeContext(request, {})
    return HttpResponse(t.render(c))

@login_required
def balance(request):
    profile = request.user.get_profile()
    balance = clientlib.get_user_balance(profile)
    address = clientlib.get_user_address(profile)
    coin_txn = profile.coin_txn.order_by('tx_timestamp')
    t = loader.get_template("coinexchange/account/balance.html")
    c = CoinExchangeContext(request, {'coin_txn': coin_txn,
                                      'balance': balance,
                                      'address': address})
    return HttpResponse(t.render(c))

class WithdrawlView(LoginView):

    def post(self, request):
        profile = request.user.get_profile()
        balance = clientlib.get_user_balance(profile)
        withdrawl_form = WithdrawlRequestForm(request.POST)
        amount = decimal.Decimal(request.POST['amount'])
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
            StatusMessages.add_warning(request, "Withdrawl result: %s" % withdrawl_result)
        else:
            pass
        t = loader.get_template("coinexchange/account/withdraw.html")
        c = CoinExchangeContext(request, {'form': withdrawl_form})
        return HttpResponse(t.render(c))

    def get(self, request):
        profile = request.user.get_profile()
        withdrawl_form = WithdrawlRequestForm()
        t = loader.get_template("coinexchange/account/withdraw.html")
        c = CoinExchangeContext(request, {'form': withdrawl_form})
        return HttpResponse(t.render(c))

class SellView(LoginView):
    def post(self, request):
        profile = request.user.get_profile()
        form = SellOfferForm(request.POST)
        if form.is_valid():
            sell = form.save(commit=False)
            sell.seller = profile
            sell.save()
            StatusMessages.add_success(request, "Bitcoin listed for sale.")
            return redirect('account_home')
        StatusMessages.add_error(request, "There were problems with the offer.")
        t = loader.get_template("coinexchange/account/sell.html")
        c = CoinExchangeContext(request, {'form': form})
        return HttpResponse(t.render(c))

    def get(self, request):
        form = SellOfferForm()
        t = loader.get_template("coinexchange/account/sell.html")
        c = CoinExchangeContext(request, {'form': form})
        return HttpResponse(t.render(c))
