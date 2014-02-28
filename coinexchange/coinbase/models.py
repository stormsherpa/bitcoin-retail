
from django.db import models
from django.contrib import admin

class ApiCreds(models.Model):
    merchant = models.OneToOneField('btc.CoinExchangeUser', related_name='coinbase_api_creds')
    access_token = models.CharField(max_length=100, null=True, blank=True)
    access_token_expire_time = models.DateTimeField(null=True, blank=True)
    refresh_token = models.CharField(max_length=100, null=True, blank=True)
    token_response = models.TextField(null=True, blank=True)
    code = models.TextField(max_length=100, null=True, blank=True)

    @classmethod
    def load_by_merchant(cls, merchant):
        try:
            return cls.objects.get(merchant=merchant)
        except cls.DoesNotExist:
            return cls(merchant=merchant)
