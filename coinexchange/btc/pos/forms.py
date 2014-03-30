
from django import forms

from coinexchange.btc.pos.models import SalesTransaction, MerchantSettings

class NewSalesTransactionForm(forms.ModelForm):
    class Meta:
        model = SalesTransaction
        fields = ['reference', 'amount']

class MerchantSettingsForm(forms.ModelForm):
#     btc_payout_address = forms.CharField(max_length=50, required=False)
    class Meta:
        model = MerchantSettings
        fields = ['exchange_rate', 'sales_volume']
#         fields = ['payout_with_coinbase', 'exchange_rate', 'btc_payout_address']
