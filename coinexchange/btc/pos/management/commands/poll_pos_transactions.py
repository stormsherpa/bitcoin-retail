
import time

from django.core.management.base import BaseCommand, CommandError

import bitcoinrpc

from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser
from coinexchange.btc import agentlib
from coinexchange.btc.config import BITCOINRPC_ARGS

from coinexchange.btc.pos import lib

def poll_transactions(conn, count=5):
    for tx in conn.listtransactions(count=count):
        tx_rec = agentlib.store_btc_tx(tx)
        if tx.category=="receive":
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

        try:
            while True:
                 poll_transactions(conn, 5)
                 time.sleep(1)
        except KeyboardInterrupt:
            print "Keyboard interrupt received.  Exiting."