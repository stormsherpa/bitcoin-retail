
from django.db import models
from django.contrib import admin
 
# from coinexchange.btc.models import CoinExchangeUser
 
class ReceiveAddress(models.Model):
    merchant = models.ForeignKey('btc.CoinExchangeUser', related_name='pos_receive_address')
    address = models.CharField(max_length=200)
    available = models.BooleanField(default=True)
  
class SalesTransaction(models.Model):
    merchant = models.ForeignKey('btc.CoinExchangeUser', related_name='sales_tx')
    reference = models.CharField(max_length=50, default="")
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=10, blank=True, default="USD")
    currency_btc_exchange_rate = models.DecimalField(max_digits=20, decimal_places=8)
    # currency_btc_exchange_rate is price of 1BTC in 'currency' units
    # btc_amount = currency/currency_btc_exchange_rate
    btc_amount = models.DecimalField(max_digits=20, decimal_places=8)
    btc_address = models.ForeignKey(ReceiveAddress, related_name='sales_tx')
    btc_request_url = models.CharField(max_length=250, null=True)
    btc_txid = models.CharField(max_length=200, null=True, unique=True)
    tx_timestamp = models.DateTimeField(auto_now_add=True)
    tx_published_timestamp = models.DateTimeField(null=True, blank=True)
