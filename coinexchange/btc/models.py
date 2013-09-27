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

class CoinExchangeUserAdmin(UserAdmin):
    inlines = (CoinExchangeUserInline, )

admin.site.unregister(User)
admin.site.register(User, CoinExchangeUserAdmin)


class CoinExchangeUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'btc_account')

class CoinTxnLog(models.Model):
    user = models.ForeignKey(CoinExchangeUser, blank=True, null=True, related_name='coin_txn')
    otheruser = models.ForeignKey(CoinExchangeUser, blank=True, null=True, related_name='other_coin_txn')
    tx_type = models.CharField(max_length=20)
    tx_account = models.CharField(max_length=200)
    tx_otheraccount = models.CharField(max_length=200)
    tx_amount = models.DecimalField(max_digits=20, decimal_places=8)
    tx_timestamp = models.DateTimeField()
    tx_description = models.TextField()
    tx_id = models.CharField(max_length=200, null=True, unique=True)
    account_address = models.CharField(max_length=200, blank=True, null=True)
    external_address = models.CharField(max_length=200, blank=True, null=True)
    record_timestamp = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.tx_id

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

# class CoinTxnStatusLog(models.Model):
#     transaction = models.ForeignKey(CoinTxnLog, related_name='tx_status')
#     status_timestamp = models.DateTimeField(auto_now_add=True)
#     tx_status = models.CharField(max_length=20)
    
# admin.site.register(CoinExchangeUser, CoinExchangeUserAdmin)

admin.site.register(CoinTxnLog, CoinTxnLogAdmin)

