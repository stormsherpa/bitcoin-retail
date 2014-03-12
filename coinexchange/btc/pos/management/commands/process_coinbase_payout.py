
import sys
import time
import datetime

from django.core.management.base import BaseCommand, CommandError

from coinexchange.btc.pos import lib

class Command(BaseCommand):
    args = ''
    help = 'Update coinbase payout transactions'

    def handle(self, *args, **kwargs):
#         lib.update_pending_coinbase_payouts()
        lib.update_batch_aggregates()
