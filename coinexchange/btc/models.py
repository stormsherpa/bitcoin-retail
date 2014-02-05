
import yaml

from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.db.models.signals import post_save


class CoinExchangeUser(models.Model):
    class Meta():
        db_table = 'coin_exchange_user'
    user = models.OneToOneField(User, related_name='+')
    btc_account = models.CharField(max_length=20, unique=True)
    btc_address = models.CharField(max_length=200, null=True, unique=True)
    btc_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    def __unicode__(self):
        return str(self.user.username)

def new_user_profile(sender, instance, created, **kwargs):
    if created:
        account_name = "user_account_%d" % instance.id
        CoinExchangeUser.objects.create(user=instance, btc_account=account_name)

post_save.connect(new_user_profile, sender=User)

class CoinExchangeUserInline(admin.StackedInline):
    readonly_fields = ['btc_account', 'btc_address']
    model = CoinExchangeUser
    can_delete = False
    verbose_name_plural = 'profile'

class CoinExchangeUserInlineAdmin(UserAdmin):
    inlines = (CoinExchangeUserInline, )

admin.site.unregister(User)
admin.site.register(User, CoinExchangeUserInlineAdmin)

class CoinExchangeUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'btc_account')

class CoinTxnLog(models.Model):
    user = models.ForeignKey(CoinExchangeUser, blank=True, null=True, related_name='coin_txn')
    otheruser = models.ForeignKey(CoinExchangeUser, blank=True, null=True, related_name='other_coin_txn')
    tx_type = models.CharField(max_length=20)
    tx_account = models.CharField(max_length=200)
    tx_otheraccount = models.CharField(max_length=200)
    tx_amount = models.DecimalField(max_digits=20, decimal_places=8)
    tx_fee = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True)
    tx_timestamp = models.DateTimeField()
    tx_description = models.TextField()
    tx_id = models.CharField(max_length=200, null=True, unique=True)
    account_address = models.CharField(max_length=200, blank=True, null=True)
    external_address = models.CharField(max_length=200, blank=True, null=True)
    record_timestamp = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.tx_id

    def otheraccount_name(self):
        if self.tx_type == "receive":
            return "(external)"
        elif self.tx_type == "send":
            return "(external)"
        elif self.tx_type == "sendfee":
            return "Fees"
        elif self.tx_otheraccount == "":
            return "(root)"
        else:
            return self.tx_otheraccount

class CoinTxnLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'otheruser', 'tx_id')
    actions = None
    readonly_fields = ['user',
                       'otheruser',
                       'tx_type',
                       'tx_account',
                       'tx_otheraccount',
                       'tx_amount',
                       'tx_timestamp',
                       'tx_description',
                       'tx_id',
                       'account_address',
                       'external_address',
                       'record_timestamp',
                       ]

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(CoinTxnLog, CoinTxnLogAdmin)

class PaymentMethod(models.Model):
    name = models.CharField(max_length=20)
    type_class = models.CharField(max_length=100)

    def __unicode__(self):
        return u'%s' % self.name

admin.site.register(PaymentMethod)

class CurrencyUnit(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name

admin.site.register(CurrencyUnit)

class SellOffer(models.Model):
    seller = models.ForeignKey(CoinExchangeUser, related_name='sell_offers')
    price = models.DecimalField(max_digits=20, decimal_places=8)
    units = models.ForeignKey(CurrencyUnit, related_name='+')
    max_btc = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    min_btc = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    is_active = models.BooleanField(default=True, blank=True)
    offer_timestamp = models.DateTimeField(auto_now_add=True)
    payment_methods = models.ManyToManyField(PaymentMethod, related_name='sell_offers')

    @property
    def available(self):
        print "available"
        balance = self.seller.btc_balance
        if balance < self.min_btc:
            return 0
        if balance > self.max_btc:
            return self.max_btc
        return balance

class SellOfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'seller')
    readonly_fields = ['seller']
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(SellOffer, SellOfferAdmin)

class CoinEscrow(models.Model):
    buyer = models.ForeignKey(CoinExchangeUser, related_name='purchases')
    seller = models.ForeignKey(CoinExchangeUser, related_name='sales')
    sell_offer = models.ForeignKey(SellOffer, null=True, blank=True, related_name='purchases')
    btc_escrow_account = models.CharField(max_length=200)
    sale_amount = models.DecimalField(max_digits=20, decimal_places=8)
    fee_amount = models.DecimalField(max_digits=20, decimal_places=8)

class CoinEscrowAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'seller', 'btc_escrow_account')
    readonly_fields = ['buyer',
                       'seller',
                       'btc_escrow_account',
                       'sale_amount',
                       'fee_amount',
                       ]

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(CoinEscrow, CoinEscrowAdmin)

class WithdrawlRequest(models.Model):
    user = models.ForeignKey(CoinExchangeUser, blank=True, related_name='withdrawl_requests')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    to_address = models.CharField(max_length=200)
    request_timestamp = models.DateTimeField(blank=True, auto_now_add=True)
    status = models.CharField(max_length=20)
    txid = models.CharField(max_length=200)

    def as_yaml(self):
        out = {'command': 'user_withdrawl',
               'account': self.user.btc_account,
               'amount': self.amount,
               'to_address': self.to_address,
               'request_id': self.id}
        return yaml.dump(out)
