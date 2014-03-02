
import json
import decimal

from django.http import HttpResponse, Http404
from django.template import loader
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.generic import View

from coinexchange.views import LoginView, JsonResponse
from coinexchange.main.lib import CoinExchangeContext, StatusMessages
from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc import clientlib

from coinexchange.btc.pos.forms import NewSalesTransactionForm, MerchantSettingsForm
from coinexchange.btc.pos.models import SalesTransaction, TransactionBatch, MerchantSettings
from coinexchange.btc.pos import lib

@login_required
def main(request):
    data = {
            'new_sales_form': NewSalesTransactionForm(),
            }
    t = loader.get_template("coinexchange/pos/main.html")
    c = CoinExchangeContext(request, data)
    return HttpResponse(t.render(c))

@login_required
def admin(request):
    profile = request.user.get_profile()
    merchant_settings = MerchantSettings.load_by_merchant(profile)
    batches = TransactionBatch.objects.filter(merchant=profile).order_by('-batch_timestamp')
    settings = MerchantSettingsForm(instance=merchant_settings)
    data = {'unbatched_tx': [x for x in lib.get_unbatched_transactions(profile)],
            'batches': [x for x in batches],
            "settings_form": settings,
            }
    t = loader.get_template("coinexchange/pos/admin.html")
    c = CoinExchangeContext(request, data)
    return HttpResponse(t.render(c))

@login_required
def merchant_settings(request):
    print request.POST
    btc_addr = request.POST.get('btc_payout_address')
    if btc_addr != '' and not clientlib.valid_bitcoin_address(btc_addr):
        data = {'error': True,
                'response': "Invalid bitcoin address given."}
    else:
        profile = request.user.get_profile()
        merchant_settings = MerchantSettings.load_by_merchant(profile)
        settings = MerchantSettingsForm(request.POST, instance=merchant_settings)
        print settings.fields['exchange_rate']
        if settings.is_valid():
            settings.save()
            data = {'error': False,
                    'response': 'ok'}
        else:
#             print settings.errors
            data = {'error': True,
                    'response': "Form validation error: %s" % settings.errors}
    http_response = HttpResponse(json.dumps(data)+"\n")
    http_response['Content-Type'] = 'application/json'
    return http_response

@login_required
def batch(request, batch_id):
    profile = request.user.get_profile()
    try:
        batch = TransactionBatch.objects.get(id=batch_id)
        if batch.merchant != profile:
            raise Http404()
    except TransactionBatch.DoesNotExist:
        raise Http404()
    transactions = [x for x in batch.transactions.order_by('tx_timestamp')]
    total_amount = 0
    total_bitcoin = decimal.Decimal(0)
    for tx in transactions:
        total_amount += tx.amount
        total_bitcoin += tx.btc_amount
    data = {'batch': batch,
            'transactions': transactions,
            'total_amount': total_amount,
            'total_bitcoin': total_bitcoin,
            'average_exchange_rate': total_amount/total_bitcoin,
            }
    t = loader.get_template("coinexchange/pos/batch.html")
    c = CoinExchangeContext(request, data)
    return HttpResponse(t.render(c))

@login_required
def make_batch(request):
    profile = request.user.get_profile()
    batch = lib.make_merchant_batch(profile)
    if batch:
        batch_tx_ids = [x.btc_txid for x in batch.transactions.all()]
        response = {"batch_tx_ids": batch_tx_ids,
                    "error": False,
                    }
    else:
        response = {"error": True,
                    "status": "No batch created.",
                    "batch_tx_ids": list()}
    http_response = HttpResponse(json.dumps(response)+"\n")
    http_response['Content-Type'] = 'application/json'
    return http_response
