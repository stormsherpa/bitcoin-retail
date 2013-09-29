
from django import forms

from coinexchange.btc.models import WithdrawlRequest

class SignupForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

class WithdrawlRequestForm(forms.ModelForm):
    class Meta:
        model = WithdrawlRequest
        fields = ('amount', 'to_address')
