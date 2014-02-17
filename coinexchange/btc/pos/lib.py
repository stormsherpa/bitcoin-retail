
import decimal
import json
import datetime
import requests

from django.template import Context, loader
from django.utils.safestring import mark_safe
from django.utils.timezone import utc

from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc import clientlib
from coinexchange.btc.pos.models import ReceiveAddress, SalesTransaction
from coinexchange import xmpp

class NewReceiveAddressException(Exception):
    pass

class ExchangeRateException(Exception):
    pass

def get_available_receive_address(merchant):
    try:
        return merchant.pos_receive_address.filter(available=True)[0]
    except IndexError:
        pass
    r = BitcoindClient.get_instance().getnewaddress(merchant.btc_account)
    if r.get('error', True):
        raise NewReceiveAddressException()
    addr = r.get('result')
    print "Returning addr: %s" % addr
    new_addr = ReceiveAddress(merchant=merchant, address=addr, available=True)
    new_addr.save()
    return new_addr

def get_exchange_rate(currency):
    r = requests.get("https://coinbase.com/api/v1/prices/spot_rate", data={'currency':currency})
    if r.status_code == 200:
        data = json.loads(r.text)
        return decimal.Decimal(data.get('amount'))
    raise ExchangeRateException()

def make_new_sale(merchant, fiat_amount, reference):
    exchange_rate = get_exchange_rate(merchant.currency)
    amount = decimal.Decimal(fiat_amount)
    btc_amount = amount/exchange_rate
    receive_address = get_available_receive_address(merchant)
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
        yield tx
