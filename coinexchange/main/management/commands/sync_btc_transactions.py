
import datetime

from django.core.management.base import BaseCommand, CommandError
from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser
from django.utils.timezone import utc

import bitcoinrpc

from coinexchange.btc import lib
from coinexchange.btc.config import BITCOINRPC_CONFIG

class Command(BaseCommand):
    args = ''
    help = 'Check bitcoin ledger for new transactions'
    
    def handle(self, *args, **options):
        conn = bitcoinrpc.connect_to_remote(*BITCOINRPC_CONFIG['args'], **BITCOINRPC_CONFIG['kwargs'])
        for tx in conn.listtransactions():
            lib.store_btc_tx(tx)

