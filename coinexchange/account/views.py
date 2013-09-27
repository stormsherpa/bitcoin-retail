
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate

from coinexchange.main.forms import SignupForm
from coinexchange.btc.models import CoinTxnLog

def home(request):
    t = loader.get_template("coinexchange/account.html")
    c = RequestContext(request, dict())
    return HttpResponse(t.render(c))

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
    c = RequestContext(request, {'form': signup_form})
    return HttpResponse(t.render(c))

def settings(request):
    t = loader.get_template("coinexchange/account/edit.html")
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

def balance(request):
    profile = request.user.get_profile()
    coin_txn = profile.coin_txn.order_by('tx_timestamp')
    t = loader.get_template("coinexchange/account/balance.html")
    c = RequestContext(request, {'coin_txn': coin_txn})
    return HttpResponse(t.render(c))
