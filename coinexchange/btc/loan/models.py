import yaml

from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin

from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser

class LoanRequest(models.Model):
    borrower = models.ForeignKey(CoinExchangeUser, related_name='loan_requests')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    loan_account = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    interest_rate = models.DecimalField(max_digits=10, decimal_places=4)
    exchange_interest = models.DecimalField(max_digits=10, decimal_places=4, default=3, blank=True)
    funding_open = models.BooleanField(default=False, blank=True)
    funding_deadline = models.DateTimeField()
    loan_created = models.BooleanField(default=False, blank=True)
    loan_paid_off = models.BooleanField(default=False, blank=True)
    request_timestamp = models.DateTimeField(auto_now_add=True)

class LoanPledge(models.Model):
    loanrequest = models.ForeignKey(LoanRequest, related_name='pledges')
    user = models.ForeignKey(CoinExchangeUser, related_name='loan_pledges')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    pledge_account_credit = models.ForeignKey(CoinTxnLog, null=True, related_name='+')
    pledge_cancelled = models.BooleanField(default=False, blank=True)
    pledge_timestamp = models.DateTimeField(auto_now_add=True)

class LoanTxnLog(models.Model):
    loan = models.ForeignKey(LoanRequest, related_name='transactions')
    tx_amount = models.DecimalField(max_digits=20, decimal_places=8)
    tx_type = models.CharField(max_length=20)
    tx_memo = models.CharField(max_length=200)
    record_timestamp = models.DateTimeField(auto_now_add=True)

class LoanPaymentSplit(models.Model):
    loan_tx = models.ForeignKey(LoanRequest, related_name='splits')
    lender = models.ForeignKey(CoinExchangeUser, null=True, related_name='+')
    to_account = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
