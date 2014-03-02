
import decimal
import json
import datetime
import requests

from django.core.cache import cache
from django.template import Context, loader
from django.utils.safestring import mark_safe
from django.utils.timezone import utc

from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc import clientlib
from coinexchange.btc.pos.models import ReceiveAddress, SalesTransaction, MerchantSettings
from coinexchange import xmpp

class NewReceiveAddressException(Exception):
    pass

class ExchangeRateException(Exception):
    pass

class CreateBatchException(Exception):
    pass

def get_available_receive_address(merchant, btc_amount=None):
    try:
        available_addresses = [x for x in merchant.pos_receive_address.filter(available=True)]
    except IndexError:
        pass
    print available_addresses
    if available_addresses:
        print "%0.8f" % decimal.Decimal(btc_amount)
        tx_list = SalesTransaction.objects.filter(merchant=merchant,
                                                  btc_amount=btc_amount,
                                                  btc_txid__isnull=True)#
        pending_tx = [t for t in tx_list]
        print [t.btc_amount for t in pending_tx]
        def available_addr(addr):
            for tx in pending_tx:
                if tx.btc_address == addr:
                    return False
            return True
        final_addresses = filter(available_addr, available_addresses)
        if final_addresses:
            return final_addresses[0]

    r = BitcoindClient.get_instance().getnewaddress(merchant.btc_account)
    if r.get('error', True):
        raise NewReceiveAddressException(json.dumps(r))
    addr = r.get('result')
    print "Returning addr: %s" % addr
    new_addr = ReceiveAddress(merchant=merchant, address=addr, available=True)
    new_addr.save()
    return new_addr

def get_merchant_exchange_rate(merchant):
    mode = None
    if merchant:
        settings = MerchantSettings.load_by_merchant(merchant)
        if settings.exchange_rate:
            mode = settings.exchange_rate.name
            print "Using configured mode: %s" % mode
    if mode in ["sell", "sell_fees"]:
        r = requests.get("https://coinbase.com/api/v1/prices/sell", data={'qty': 1})
        if r.status_code == 200:
            data = r.json()
            print data
            sell_price = data['subtotal'].get('amount')
            sell_fees_price = data.get('amount')
            if mode == "sell":
                return decimal.Decimal(sell_price)
            return decimal.Decimal(sell_fees_price)
        raise ExchangeRateException("Could not get sell prices from coinbase.")
    else:
        if not mode:
            print "Mode unconfigured.  Using spot."
        spot_req_args = {'currency': merchant.currency}
        r = requests.get("https://coinbase.com/api/v1/prices/spot_rate", data=spot_req_args)
        if r.status_code == 200:
            data = json.loads(r.text)
            return decimal.Decimal(data.get('amount'))
        else:
            raise ExchangeRateException("Could not get spot price from coinbase.")


def get_exchange_rate(currency):
    r = requests.get("https://coinbase.com/api/v1/prices/spot_rate", data={'currency':currency})
    if r.status_code == 200:
        data = json.loads(r.text)
        return decimal.Decimal(data.get('amount'))
    raise ExchangeRateException()

def make_new_sale(merchant, fiat_amount, reference):
    exchange_rate = get_merchant_exchange_rate(merchant)
    amount = decimal.Decimal(fiat_amount)
    btc_amount = decimal.Decimal("%0.8f" % (amount/exchange_rate))
    receive_address = get_available_receive_address(merchant, btc_amount=btc_amount)
    btc_url = "bitcoin:%s?amount=%0.8f" % (receive_address.address, btc_amount)
    sale = SalesTransaction(merchant=merchant,
                            reference=reference,
                            amount=amount,
                            currency=merchant.currency,
                            currency_btc_exchange_rate=exchange_rate,
                            btc_amount=btc_amount,
                            btc_address=receive_address,
                            btc_request_url=btc_url)
    sale.save()
    return sale

def sale_json(sale):
    response = {
            'reference': sale.reference,
            'sale_id': sale.id,
            'address': sale.btc_address.address,
            'currency': sale.currency,
            'fiat_amount': "%0.2f" % sale.amount,
            'btc_amount': "%0.8f" % sale.btc_amount,
            'btc_request_url': sale.btc_request_url,
            'pending': bool(not sale.btc_txid),
            }
    return response

def match_pending_transaction(tx, tx_rec):
    try:
        rx_addr = ReceiveAddress.objects.get(address=tx.address)
    except ReceiveAddress.DoesNotExist:
        return None
#     print "match_pending_transaction: %s" % tx.txid
#     print tx
    try:
        tx_list = SalesTransaction.objects.filter(btc_address=rx_addr,
                                               btc_amount=tx.amount,
                                               btc_txid__isnull=True)
    except SalesTransaction.DoesNotExist:
        return None
    if not tx_list:
        return None
    s_tx = tx_list[0]
    print "Found sales tx: %s" % tx.txid
    return s_tx

def process_btc_transaction(tx, tx_rec, sales_tx):
    sales_tx.btc_txid = tx.txid
    tstamp = datetime.datetime.fromtimestamp(tx.time, utc)
    sales_tx.tx_published_timestamp = tstamp
    sales_tx.save()

def notify_transaction(sales_tx, status):
    t = loader.get_template("coinexchange/xmpp/pos_confirm.xml")
    body = {'sale_id': sales_tx.id,
            'status': status
            }
    c = Context({'tx': sales_tx,
                 'json_body': mark_safe(json.dumps(body)),
                 'to': xmpp.get_userjid(sales_tx.merchant.user)})
    xmpp.send_message(t.render(c))

def get_unbatched_transactions(merchant):
    open_tx = SalesTransaction.objects.filter(batch__isnull=True,
                                              btc_txid__isnull=False,
                                              merchant=merchant).order_by('tx_timestamp')
    for tx in open_tx:
        tx.tx_detail = clientlib.get_tx_confirmations(tx.btc_txid)
        print tx.tx_detail
        yield tx
