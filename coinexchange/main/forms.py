
from django import forms

from coinexchange.btc.models import WithdrawlRequest, SellOffer

class SignupForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

class WithdrawlRequestForm(forms.ModelForm):
    class Meta:
        model = WithdrawlRequest
        fields = ('amount', 'to_address')

class SellOfferForm(forms.ModelForm):
    class Meta:
        model = SellOffer
        fields = ('price', 'units', 'max_btc', 'min_btc', 'payment_methods', 'is_active')

class BuyForm(forms.Form):
    amount = forms.DecimalField()
