
import time
import datetime
# import objgraph

from django.core.management.base import BaseCommand, CommandError

import bitcoinrpc

from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser
from coinexchange.btc import agentlib
from coinexchange.btc.config import BITCOINRPC_ARGS

from coinexchange.btc.pos import lib

def find_tx_parent(conn, tx):
    if tx.confirmations == 0:
        return None
    try:
        extra = conn.getrawtransaction(tx.txid)
    except bitcoinrpc.exceptions.InvalidAddressOrKey:
#         print "Invalid tx: %s -> %0.8f" % (tx.txid, tx.amount)
        return None
#     print "====================="
#     print "TX: %s" % tx.txid
#     print "Raw: %s" % extra
#     print "Details: %s" % tx.details
#     print dir(extra)

my_processed_tx_list = list()

def poll_transactions(conn, count=5):
    for tx in conn.listtransactions(count=count):
        if tx.category in ['receive', 'send'] and not tx.txid in my_processed_tx_list:
            tx_rec = agentlib.store_btc_tx(tx)
            my_processed_tx_list.append(str(tx.txid))
            print "%s: Processing tx: %s" % (datetime.datetime.now(), tx.txid)
            if tx.category=="receive":
    #             find_tx_parent(conn, tx)
                sales_tx = lib.match_pending_transaction(tx,tx_rec)
                if sales_tx:
                    print "Processing tx: %s" % tx.txid
                    lib.process_btc_transaction(tx, tx_rec, sales_tx)
                    lib.notify_transaction(sales_tx, "confirmed")

def next_timeout(interval):
    return int(time.time())+interval

class Command(BaseCommand):
    args = ''
    help = 'Poll for Transactions'

    def handle(self, *args, **options):
        if BITCOINRPC_ARGS:
            conn = bitcoinrpc.connect_to_remote(*BITCOINRPC_ARGS['args'], **BITCOINRPC_ARGS['kwargs'])
        else:
            conn = bitcoinrpc.connect_to_local()
        poll_transactions(conn, 50)
        expire_time = next_timeout(5)
        try:
            while True:
                poll_transactions(conn, 5)
                time.sleep(1)
                if int(time.time()) > expire_time:
                    expire_time = next_timeout(3600)
                    print "=========== %s ===========" % datetime.datetime.now()
#                     objgraph.show_most_common_types(limit=5)
#                  print "Tick..."
        except KeyboardInterrupt:
            print "Keyboard interrupt received.  Exiting."
