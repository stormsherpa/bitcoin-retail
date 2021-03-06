
import decimal
import json
import datetime
import traceback
import time

import requests

from django.core.cache import cache
from django.template import Context, loader
from django.utils.safestring import mark_safe
from django.utils.timezone import utc
from django.core.urlresolvers import reverse
from django.conf import settings

from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc import clientlib
from coinexchange.btc.pos.models import ReceiveAddress, SalesTransaction, MerchantSettings, TransactionBatch, UnexpectedPaymentNotification
from coinexchange import xmpp
from coinexchange import coinbase
from coinexchange.coinbase.models import ApiCreds
from coinexchange.btc.queue import CoinexchangePublisher

class NewReceiveAddressException(Exception):
    pass

class ExchangeRateException(Exception):
    pass

class CreateBatchException(Exception):
    pass

def get_available_receive_address(merchant, btc_amount=None):
    msettings = MerchantSettings.load_by_merchant(merchant)
    try:
        available_addresses = [x for x in merchant.pos_receive_address.filter(available=True,
                                                                              coinbase_address=msettings.coinbase_wallet)]
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
    if msettings.coinbase_wallet:
        coinbase_api = coinbase.get_api_instance(merchant)
        new_addr = ReceiveAddress(merchant=merchant, address='1',
                                  available=True,
                                  coinbase_address=True)
        new_addr.save()
        callback_url = "%s%s" % (settings.SITE_HOSTNAME,
                                 reverse('coinbase_recv_callback', args=[new_addr.id]))
        cb_addr = coinbase_api.generate_receive_address(callback_url=callback_url)
        new_addr.address = cb_addr
        new_addr.save()
        return new_addr
    else:
        r = BitcoindClient.get_instance().getnewaddress(merchant.btc_account)
        if r.get('error', True):
            raise NewReceiveAddressException(json.dumps(r))
        addr = r.get('result')
        print "Returning addr: %s" % addr
        new_addr = ReceiveAddress(merchant=merchant, address=addr, available=True, coinbase_address=False)
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
        msettings = MerchantSettings.load_by_merchant(merchant)
        if msettings.exchange_rate:
            mode = msettings.exchange_rate.name
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
                            btc_request_url=btc_url,
                            coinbase_api_tx=receive_address.coinbase_address)
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

def save_unexpected_payment(payment):
    p = UnexpectedPaymentNotification(merchant=payment.receive_address.merchant,
                                      body=payment._raw_text)
    p.save()
    return p

def process_coinbase_payment_notification(payment):
    print "Processing payment notification - address_id: %s" % payment.receive_address.id
    print "payment amount: %s (%s)" % (payment.amount, payment.amount.__class__)
    if not payment.receive_address:
        print "Receive address was not found! (%s)" % payment.address
        return save_unexpected_payment(payment)
    try:
        tx_list = SalesTransaction.objects.filter(btc_address=payment.receive_address,
                                                  btc_amount=decimal.Decimal("%s" % payment.amount),
                                                  btc_txid__isnull=True)
#         print [x for x in tx_list if decimal.Decimal(x.btc_amount) == decimal.Decimal(payment.amount)]
#         print tx_list
#         raise Exception("Not done")
    except SalesTransaction.DoesNotExist:
        print "Unexpected payment notification from coinbase."
        return save_unexpected_payment(payment)
    except Exception as e:
        print "%s: %s" %(e.__class__, e)
        traceback.print_exc()
        raise e
    if not tx_list:
        return False
    s_tx = tx_list[0]
    print "Found sales_tx: %s" % s_tx.id
    s_tx.btc_txid = payment.transaction_hash
#     tstamp = datetime.datetime.fromtimestamp(tx.time, utc)
    tstamp = datetime.datetime.fromtimestamp(time.time(), utc)
    s_tx.tx_published_timestamp = tstamp
    s_tx.coinbase_txid = payment.transaction_id
    s_tx.save()
    return s_tx

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
        yield tx

def serialize_coinbase_transaction(tx):
    out = dict()
    keys = ['amount', 'created_at', 'notes', 'recipient_address',
            'recipient_type', 'request', 'status', 'transaction_id']
    for k in keys:
        out[k] = getattr(tx, k, None)
    return out

def make_merchant_batch(merchant):
    merchant_settings = MerchantSettings.load_by_merchant(merchant)
    coinbase_api = coinbase.get_api_instance(merchant)
    batch_tx_list = list()
    for tx in get_unbatched_transactions(merchant):
        tx.coinbase_tx_detail = coinbase_api.get_transaction(tx.coinbase_txid)
        if tx.coinbase_tx_detail.status == "complete":
            batch_tx_list.append(tx)
    if not batch_tx_list:
        raise CreateBatchException("No transactions available for batching.")
    total_btc = sum([x.btc_amount for x in batch_tx_list])
    total_amount = sum([x.amount for x in batch_tx_list])
    print total_btc
    print total_amount
    print batch_tx_list
    avg_exchange_rate = decimal.Decimal(total_amount)/decimal.Decimal(total_btc)
    batch = TransactionBatch(merchant=merchant,
                             btc_amount=total_btc,
                             btc_address="coinbase",
                             captured_amount=total_amount,
                             captured_avg_exchange_rate=avg_exchange_rate,
                             btc_tx_fee=0,
                             coinbase_payout=merchant_settings.payout_with_coinbase)
    batch.save()
    for tx in batch_tx_list:
        tx.batch = batch
        tx.save()

    msg = json.dumps({'command': 'payout_batch', 'batch_id': batch.id})
    publish = CoinexchangePublisher.get_instance('payment_batches').send(msg)
    if publish:
        return batch
    else:
        raise CreateBatchException("Post processing queue unavailable.  Cancelling batch.")

def calc_batch_fee(batch):
    print "1"
    btc_tx_fee= batch.btc_amount * decimal.Decimal(settings.SERVICE_FEE_MULTIPLIER)
    exchange_rate = get_exchange_rate('sell')
    usd_amount = exchange_rate * btc_tx_fee
    min_fee = decimal.Decimal(settings.SERVICE_FEE_MINIMUM)
    if usd_amount < min_fee:
        btc_tx_fee = min_fee/exchange_rate
    print "Calc fee: %s" % btc_tx_fee
    return btc_tx_fee

def pay_coinbase_batch(batch):
    if batch.coinbase_payout and batch.coinbase_txid and batch.received_amount:
        print "Batch %s already processed!"
        return
    api = coinbase.get_api_instance(batch.merchant)
    btc_tx_fee = calc_batch_fee(batch)
    realized_btc_amount_long = batch.btc_amount - btc_tx_fee
    realized_btc_amount = float("%.8f" % realized_btc_amount_long)
    print "Batch amount:     %.8f" % batch.btc_amount
    print "Coinexchange fee: %.8f" % btc_tx_fee
    print "Total paid:       %.8f" % realized_btc_amount
    batch.btc_tx_fee = btc_tx_fee
    batch.realized_btc_amount = realized_btc_amount
    tx_fee_usd = batch.captured_amount/batch.btc_amount*btc_tx_fee
    print "Coinexchange USD: %.2f" % tx_fee_usd
    print "Pay service fee."
    try:
        transaction_params = dict() #{'idem': "batch_id=%s" % batch.id}
        real_btc_tx_fee = btc_tx_fee
        if btc_tx_fee < .01:
            print "Deducting send fee of .0002 for small payment. (< .01 BTC)"
            transaction_params['user_fee'] = "0.0002"
            real_btc_tx_fee -= decimal.Decimal(.0002)
        service_fee = api.send(settings.SERVICE_FEE_ADDRESS,
                               float("%.8f" % real_btc_tx_fee),
                               transaction_params=transaction_params)
        print "Service fee tx: %s -> %s" % (service_fee.amount,
                                            service_fee.transaction_id)
    except Exception as e:
        traceback.print_exc()

        print "%s: %s" % (e.__class__, e)
        raise e
    sell_tx = api.sell_btc(realized_btc_amount)
    batch.coinbase_txid = sell_tx.transaction_id
    print "sold: %s" % sell_tx.transaction_id
    print "  %s bitcoin was sold for %s" % (sell_tx.btc_amount, sell_tx.total_amount)
    fees = (sell_tx.fees_coinbase + sell_tx.fees_bank)/100
    print "  $%.2f fees" % fees
    print "   Subtotal amount: %s" % sell_tx.subtotal_amount
    print "   Total amount:    %s" % sell_tx.total_amount
    exchange_rate_long = sell_tx.subtotal_amount/sell_tx.btc_amount
    exchange_rate = float("%.2f" % exchange_rate_long)
    print "   Exchange rate:   %s" % exchange_rate
    batch.batch_amount = sell_tx.subtotal_amount
    batch.exchange_fees = fees
    batch.received_amount = sell_tx.total_amount
    batch.save()

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

class TransactionBatchReport():
    def __init__(self, merchant, start_date, end_date):
        print "Batch report: %s -> %s" % (start_date, end_date)
        self.start_datetime = datetime.datetime.strptime(start_date, "%m/%d/%Y")
        self.start_date = self.start_datetime.date()
        self.end_datetime = datetime.datetime.strptime(end_date, "%m/%d/%Y")
        self.end_date = self.end_datetime.date()
        batch_list = TransactionBatch.objects.filter(merchant=merchant,
                                                     batch_timestamp__lte=self.end_date,
                                                     batch_timestamp__gte=self.start_date)
        self.batch_list = [x for x in batch_list.order_by('batch_timestamp')]
        self.total_captured = 0
        self.total_realized = 0
        self.total_btc = 0
        self.aggregate_gain = 0
        self.btc_tx_fees = 0
        self.exchange_fees = 0
        self.total_received = 0
        for b in self.batch_list:
            self.total_captured += b.captured_amount
            self.total_realized += b.total_realized_value or 0
            self.total_btc += b.btc_amount
            print b.realized_gain
            self.aggregate_gain += b.realized_gain or 0
            self.btc_tx_fees += b.realized_btc_tx_fee or 0
            self.exchange_fees += b.exchange_fees
            self.total_received += b.received_amount or 0
        self.captured_exchange_rate = self.total_captured/self.total_btc
        self.realized_exchange_rate = self.total_realized/self.total_btc
        self.total_gain = self.total_realized-self.total_captured
        self.total_gain_percent = self.total_gain/self.total_captured*100
