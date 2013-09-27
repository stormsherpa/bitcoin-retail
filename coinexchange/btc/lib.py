import datetime

from django.core.management.base import BaseCommand, CommandError
from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser
from django.utils.timezone import utc

def get_account_user(account):
    try:
        return CoinExchangeUser.objects.get(btc_account=account)
    except CoinExchangeUser.DoesNotExist:
        return None

def store_btc_tx(tx):
    if tx.category == "receive":

        try:
            db_tx = CoinTxnLog.objects.get(tx_id = tx.txid)
            print "Found: %s" % tx
            return None
        except CoinTxnLog.DoesNotExist:
            pass
        if tx.confirmations < 20:
            print "New transaction found, but has insufficient confirmations."
            return None

        print "Creating log entry for %s" % tx.txid
        
        tstamp = datetime.datetime.fromtimestamp(tx.timereceived, utc)

        tx_log = CoinTxnLog(tx_id = tx.txid,
                            user = get_account_user(tx.account),
                            tx_type=tx.category,
                            tx_account=tx.account,
                            tx_amount=tx.amount,
                            tx_timestamp=tstamp)

        tx_log.save()

    elif tx.category == "move":
        tstamp = datetime.datetime.fromtimestamp(tx.time, utc)
        to_user = get_account_user(tx.account)
        from_user = get_account_user(tx.otheraccount)
        try:
            db_tx = CoinTxnLog.objects.get(tx_type=tx.category,
                                           user=to_user,
                                           otheruser=from_user,
                                           tx_timestamp=tstamp,
                                           tx_account=tx.account,
                                           tx_otheraccount=tx.otheraccount,
                                           tx_amount=tx.amount)
            print "Found: %s" % tx
            return None
        except CoinTxnLog.DoesNotExist:
            pass
        print "Move transaction: %s" % tx
        tx_log = CoinTxnLog(tx_type=tx.category,
                            tx_amount=tx.amount,
                            user=to_user,
                            otheruser=from_user,
                            tx_account=tx.account,
                            tx_otheraccount=tx.otheraccount,
                            tx_timestamp=tstamp)
        tx_log.save()
