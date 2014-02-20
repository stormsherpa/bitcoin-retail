
import time

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
        print "Invalid tx: %s -> %0.8f" % (tx.txid, tx.amount)
        return None
    print "====================="
    print "TX: %s" % tx
    print "Raw: %s" % extra
#     print "Details: %s" % tx.details
#     print dir(extra)

def poll_transactions(conn, count=5):
    for tx in conn.listtransactions(count=count):
        tx_rec = agentlib.store_btc_tx(tx)
        if tx.category=="receive":
            find_tx_parent(conn, tx)
            sales_tx = lib.match_pending_transaction(tx,tx_rec)
            if sales_tx:
                lib.process_btc_transaction(tx, tx_rec, sales_tx)
                lib.notify_transaction(sales_tx, "confirmed")

class Command(BaseCommand):
    args = ''
    help = 'Poll for Transactions'

    def handle(self, *args, **options):
        conn = bitcoinrpc.connect_to_remote(*BITCOINRPC_ARGS['args'], **BITCOINRPC_ARGS['kwargs'])
        poll_transactions(conn, 50)
#         return
        try:
            while True:
                 poll_transactions(conn, 5)
                 time.sleep(5)
        except KeyboardInterrupt:
            print "Keyboard interrupt received.  Exiting."