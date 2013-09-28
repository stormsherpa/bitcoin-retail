
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import utc

import bitcoinrpc

from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser
from coinexchange.btc import agentlib
from coinexchange.btc.config import BITCOINRPC_ARGS

class Command(BaseCommand):
    args = ''
    help = 'Check bitcoin ledger for new transactions'
    
    def handle(self, *args, **options):
        conn = bitcoinrpc.connect_to_remote(*BITCOINRPC_ARGS['args'], **BITCOINRPC_ARGS['kwargs'])
        for tx in conn.listtransactions():
            agentlib.store_btc_tx(tx)

