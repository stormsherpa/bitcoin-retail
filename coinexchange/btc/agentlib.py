import datetime
import decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import utc

from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser
from coinexchange.btc.pos.models import TransactionBatch, SalesTransaction
from coinexchange.btc.pos import lib as pos_lib

def get_account_user(account):
    try:
        return CoinExchangeUser.objects.get(btc_account=account)
    except CoinExchangeUser.DoesNotExist:
        return None

def store_btc_tx(tx):
    if tx.category == "receive":

        tstamp = datetime.datetime.fromtimestamp(tx.timereceived, utc)

        try:
            db_tx = CoinTxnLog.objects.get(tx_id = tx.txid)
#             print "Found: %s" % tx
            return None
        except CoinTxnLog.DoesNotExist:
            pass
        if tx.confirmations < 0:
            print "New transaction found, but has insufficient confirmations."
            print "---> txid=%s to %s has %s confirmations needs %s" % (tx.txid,
                                                                        tx.account,
                                                                        tx.confirmations,
                                                                        0)
            return None

        print "Creating log entry for %s" % tx.txid
        
        tx_log = CoinTxnLog(tx_id = tx.txid,
                            user = get_account_user(tx.account),
                            tx_type=tx.category,
                            tx_account=tx.account,
                            tx_amount=tx.amount,
                            tx_timestamp=tstamp)

        tx_log.save()
        return tx_log

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
#             print "Found: %s" % tx
            return db_tx
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
        return tx_log
    elif tx.category == "send":

        tstamp = datetime.datetime.fromtimestamp(tx.time, utc)

        try:
#             print "Checking for send fee on %s" % tx
            db_tx = CoinTxnLog.objects.get(user = get_account_user(tx.account),
                                           tx_type="sendfee",
                                           tx_amount=tx.fee,
                                           tx_fee=-tx.fee,
                                           tx_timestamp=tstamp)
        except CoinTxnLog.DoesNotExist:
#             if tx.confirmations > 5:
            print "Add txn: %s" % tx.confirmations
            tx_log = CoinTxnLog(user=get_account_user(tx.account),
                                tx_type="sendfee",
                                tx_amount=tx.fee,
                                tx_fee=-tx.fee,
                                tx_timestamp=tstamp)
            tx_log.save()
        try:
            db_tx = CoinTxnLog.objects.get(tx_id=tx.txid)
            return db_tx
        except CoinTxnLog.DoesNotExist:
            pass
#         if tx.confirmations < 5:
#             print "Send request has insufficient confirmations."
#             print "---> txid=%s to %s has %s confirmations needs %s" % (tx.txid,
#                                                                         tx.account,
#                                                                         tx.confirmations,
#                                                                         5)
#             return None

        print "Creating log entry for %s" % tx.txid

        tx_log = CoinTxnLog(tx_id = tx.txid,
                            user = get_account_user(tx.account),
                            tx_type = tx.category,
                            tx_account=tx.account,
                            tx_amount=tx.amount,
                            tx_fee=tx.fee,
                            tx_timestamp=tstamp)
        tx_log.save()
        return tx_log
    else:
        print "Unknown transaction type: %s" % tx
        return None

def create_batch_record(txid_in, to_addr):
    try:
        tx_list = [SalesTransaction.objects.get(btc_txid=x) for x in txid_in]
    except TransactionBatch.DoesNotExist as e:
        raise e
    merchant = tx_list[0].merchant
    btc_amount = decimal.Decimal(0)
    for tx in tx_list:
        if merchant != tx.merchant:
            raise pos_lib.CreateBatchException("Input transactions don't all belong to the same merchant!")
        btc_amount += tx.btc_amount
    batch = TransactionBatch(merchant=merchant,
                             btc_amount=btc_amount,
                             btc_address=to_addr)
    batch.save()
    for tx in tx_list:
        tx.batch = batch
        tx.save()
    return batch

def send_all_tx_inputs(rpcconn, txid_in, to_addr):
    tx_list = [rpcconn.gettransaction(x) for x in txid_in]
    total = decimal.Decimal(0)
    tx_in = list()
    for tx in tx_list:
        print "Adding %0.8f" % tx.amount
        total += tx.amount
        tx_in.append({"txid": tx.txid, "vout": 0})
    print "Total  %0.8f" % total
    print tx_in
#     total_str = "%0.8f" % total
    test_raw_tx = rpcconn.createrawtransaction(tx_in, {to_addr: float(total)})
    tx_size = (len(test_raw_tx)/1000)+1
    tx_fee = decimal.Decimal(0.0001)*decimal.Decimal(tx_size)
    print "Size in k: %s" % tx_size
    print "Fee: %0.8f" % tx_fee
    fee_total = total-tx_fee
    final_raw_tx = rpcconn.createrawtransaction(tx_in, {to_addr: float(fee_total)})
    signed_tx = rpcconn.signrawtransaction(final_raw_tx)
    print signed_tx
    print rpcconn.decoderawtransaction(signed_tx["hex"])
    response = {'txid': rpcconn.sendrawtransaction(signed_tx["hex"]),
                'tx_fee': tx_fee,
                'tx_total': total,
                }
    print response
    return response
#     print "Length: %s" % len(response)
