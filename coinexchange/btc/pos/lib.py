
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
from coinexchange.btc.pos.models import ReceiveAddress, SalesTransaction, MerchantSettings, TransactionBatch
from coinexchange import xmpp
from coinexchange import coinbase
from coinexchange.coinbase.models import ApiCreds

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

def get_exchange_rate(mode, currency="USD"):
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
        spot_req_args = {'currency': currency}
        r = requests.get("https://coinbase.com/api/v1/prices/spot_rate", data=spot_req_args)
        if r.status_code == 200:
            data = json.loads(r.text)
            return decimal.Decimal(data.get('amount'))
        else:
            raise ExchangeRateException("Could not get spot price from coinbase.")

def get_merchant_exchange_rate(merchant):
    mode = None
    if merchant:
        settings = MerchantSettings.load_by_merchant(merchant)
        if settings.exchange_rate:
            mode = settings.exchange_rate.name
            print "Using configured mode: %s" % mode
    return get_exchange_rate(mode, currency=merchant.currency)


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

def make_merchant_batch(merchant):
    merchant_settings = MerchantSettings.load_by_merchant(merchant)
    if merchant_settings.payout_with_coinbase:
        coinbase_api = coinbase.get_api_instance(merchant)
        payout_address = coinbase_api.receive_address
    else:
        payout_address = merchant_settings.btc_payout_address
    if not clientlib.valid_bitcoin_address(payout_address):
        raise CreateBatchException("Invalid payout address.")
#     raise CreateBatchException("Merchant batch cancel: %s" % payout_address)
    batch_tx = [x for x in get_unbatched_transactions(merchant)]
    batch_tx_ids = [x.btc_txid for x in batch_tx if (x.tx_detail.confirmations >= 3)]
    if batch_tx_ids:
        raw_tx = clientlib.send_all_tx_inputs(batch_tx_ids, payout_address)
        print raw_tx
        batch = TransactionBatch.objects.get(id=raw_tx.get('batch_id'))
        batch.coinbase_payout = merchant_settings.payout_with_coinbase
        batch.save()
        return batch

def find_sell_transfer(tx, api):
    for t in api.transfers():
        print "    Transfer is %s" % t.transaction_id
#         print t.btc_amount == tx.amount
        if t.btc_amount == tx.amount:
            print "  Sell transfer is %s" % t.transaction_id
            return t
    return None

def update_pending_coinbase_payouts():
    pending = TransactionBatch.objects.filter(coinbase_payout=True,
                                              coinbase_txid__isnull=True)
    for p in pending:
        api = coinbase.get_api_instance(p.merchant)
        print "Pending batch: %s" % p.id
        paid_amount = p.btc_amount-p.btc_tx_fee
        for tx in api.transactions():
            if tx.amount == float(paid_amount):
                p.coinbase_txid = tx.transaction_id
                p.save()
                print "  Found transaction: %s" % tx.transaction_id
                break

    selling = TransactionBatch.objects.filter(coinbase_payout=True,
                                              coinbase_txid__isnull=False,
                                              received_amount__isnull=True)

    for s in selling:
        print "Selling batch: %s" % s.id
        api = coinbase.get_api_instance(s.merchant)
        tx = api.get_transaction(s.coinbase_txid)
        print "  Transfer to coinbase is '%s' with amount: %s" % (tx.status, tx.amount)
        if tx.status == "complete":
            sell_tx = find_sell_transfer(tx, api)
            if not sell_tx:
                print "  No sell transfer found.  Selling %s bitcoin." % tx.amount
                sell_tx = api.sell_btc(tx.amount)
            if not sell_tx:
                continue
            print "  %s bitcoin was sold for %s" % (sell_tx.btc_amount, sell_tx.total_amount)
            fees = (sell_tx.fees_coinbase + sell_tx.fees_bank)/100
            print "  $%.2f fees" % fees
            print "   Subtotal amount: %s" % sell_tx.subtotal_amount
            print "   Total amount:    %s" % sell_tx.total_amount
            exchange_rate_long = sell_tx.subtotal_amount/sell_tx.btc_amount
            exchange_rate = float("%.2f" % exchange_rate_long)
            print "   Exchange rate:   %s" % exchange_rate
#             print dir(sell_tx)
            s.batch_amount = sell_tx.subtotal_amount
            s.exchange_fees = fees
            s.received_amount = sell_tx.total_amount
            s.save()

def update_batch_aggregates():
    batch_query = """SELECT * FROM pos_transactionbatch where
                     (batch_amount is not null and exchange_fees is not null and
                      received_amount is not null)
                     and 
                     (captured_amount is null or realized_btc_amount is null or
                      captured_avg_exchange_rate is null or realized_gain is null or
                      exchange_rate is null or realized_btc_tx_fee is null)
                     """
    batches = TransactionBatch.objects.raw(batch_query)
    for b in batches:
        print "Updating aggregates for batch: %s" % b.id
        amount = 0
        btc_amount = 0
        for tx in b.transactions.all():
            amount += tx.amount
            btc_amount += tx.btc_amount
        b.captured_amount = amount
        b.realized_btc_amount = b.btc_amount - b.btc_tx_fee
        b.captured_avg_exchange_rate = amount/btc_amount
        b.exchange_rate = b.batch_amount/b.realized_btc_amount
        b.realized_btc_tx_fee = b.btc_tx_fee * b.exchange_rate
        b.realized_gain = (b.exchange_rate*b.btc_amount) - b.captured_amount
        b.save()
