
from django.forms import ModelForm

from coinexchange.btc.pos.models import SalesTransaction

class NewSalesTransactionForm(ModelForm):
    class Meta:
        model = SalesTransaction
        fields = ['reference', 'currency', 'amount']
