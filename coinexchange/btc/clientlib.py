import datetime
import decimal

from django.utils.timezone import utc

from coinexchange.btc.models import CoinTxnLog
from coinexchange.btc.queue.bitcoind_client import BitcoindClient

def get_user_address(exchange_user, save_if_found=True):
    if not exchange_user.btc_address:
        response = BitcoindClient.get_instance().getaccountaddress(exchange_user.btc_account)
        if not response.get('error', True):
            exchange_user.btc_address = response.get('result', None)
            if save_if_found:
                exchange_user.save()
    return exchange_user.btc_address

def get_user_balance(exchange_user):
    response = BitcoindClient.get_instance().getbalance(exchange_user.btc_account)
    balance = response.get('result', None)
    if isinstance(balance, (int, long, float, decimal.Decimal)):
        dec_balance = decimal.Decimal(balance)
        if exchange_user.btc_balance != dec_balance:
            exchange_user.btc_balance = dec_balance
            exchange_user.save()
    return balance

def move_btc(from_account, to_account, amount):
    btclient = BitcoindClient.get_instance()
    result = btclient.rescan_transactions(profile.btc_account)
    if not result.get('error', True):
        last_tx_time = result.get('result', 0)
        tstamp = datetime.datetime.fromtimestamp(last_tx_time, utc)
        from_tx = CoinTxnLog.objects.get(tx_type='move',
                                         tx_amount=amount,
                                         tx_timestamp=tstamp,
                                         tx_account=from_account)
        to_tx = CoinTxnLog.objects.get(tx_type='move',
                                       tx_amount=amount,
                                       tx_timestamp=tstamp,
                                       tx_account=to_account)
        return from_tx, to_tx
    return None, None

def send_to_escrow(buyer, seller, amount):
    (from_tx, to_tx) = move_btc(buyer.btc_account, 'escrow', amount)
    pass
