
import json
import decimal

from django.db import models
from django.contrib import admin

from django.db.models.signals import post_syncdb
 
# from coinexchange.btc.models import CoinExchangeUser
 
class ReceiveAddress(models.Model):
    merchant = models.ForeignKey('btc.CoinExchangeUser', related_name='pos_receive_address')
    address = models.CharField(max_length=200)
    available = models.BooleanField(default=True)
    coinbase_address = models.BooleanField(default=False)

class ExchangeRate(models.Model):
    name = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=100)

    def __unicode__(self):
        return self.label

def insure_exchange_rates_exist(*args, **kwargs):
    expected_entries = {'spot': "Coinbase Spot Price",
                        'sell': "Coinbase Sell Price",
                        'sell_fees': "Coinbase Sell Price Less Fees"}
    for name in expected_entries.keys():
        try:
            ExchangeRate.objects.get(name=name)
        except ExchangeRate.DoesNotExist:
            er = ExchangeRate(name=name, label=expected_entries[name])
            er.save()

post_syncdb.connect(insure_exchange_rates_exist)

class MerchantSettings(models.Model):
    merchant = models.OneToOneField('btc.CoinExchangeUser', related_name='merchant_settings')
    payout_with_coinbase = models.BooleanField(default=False, blank=True)
    exchange_rate = models.ForeignKey(ExchangeRate, null=True, blank=True)
    btc_payout_address = models.CharField(max_length=200, default='', blank=True)
    coinbase_wallet = models.BooleanField(default=True, blank=True)

    @classmethod
    def load_by_merchant(cls, merchant):
        try:
            return cls.objects.get(merchant=merchant)
        except cls.DoesNotExist:
            return cls(merchant=merchant)

class TransactionBatch(models.Model):
    merchant = models.ForeignKey('btc.CoinExchangeUser', related_name='pos_batches')
    batch_timestamp = models.DateTimeField(auto_now_add=True)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    batch_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    exchange_fees = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    received_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    currency = models.CharField(max_length=10, blank=True, default="USD")
    txid = models.CharField(max_length=200, null=True, blank=True)
    btc_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    btc_tx_fee = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    btc_address = models.CharField(max_length=200, null=True, blank=True)
    coinbase_txid = models.CharField(max_length=50, null=True, blank=True)
    coinbase_payout = models.BooleanField(default=False, blank=True)
    captured_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    captured_avg_exchange_rate = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    realized_gain = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    realized_btc_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    realized_btc_tx_fee = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)

    @property
    def total_realized_value(self):
        try:
            return decimal.Decimal(self.exchange_rate * self.btc_amount)
        except:
            return None

    @property
    def gain_percent(self):
        try:
            return decimal.Decimal(self.realized_gain/self.batch_amount)*100
        except:
            return 0

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
    batch = models.ForeignKey(TransactionBatch,
                              blank=True,
                              default=None,
                              null=True,
                              related_name='transactions')
    coinbase_txid = models.CharField(max_length=30, null=True, blank=True, default=None)
    coinbase_api_tx = models.BooleanField(default=False, blank=True)

class PaymentNotification():
    def __init__(self, json_text):
        self._raw_text = json_text
        self._raw_notification = json.loads(json_text)
        self.address = self._raw_notification.get('address')
        self.amount = self._raw_notification.get('amount')
        try:
            self.receive_address = ReceiveAddress.objects.get(address=self.address)
        except ReceiveAddress.DoesNotExist:
            self.receive_address = None
        transaction = self._raw_notification.get('transaction', dict())
        for k in transaction.keys():
            label = "transaction_%s" % k
            setattr(self, label, transaction[k])

class UnexpectedPaymentNotification(models.Model):
    merchant = models.ForeignKey('btc.CoinExchangeUser', null=True, related_name='unexpected_payment')
    body = models.TextField()
