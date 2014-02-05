
from django.core.management.base import BaseCommand, CommandError

from coinexchange.btc.models import CoinExchangeUser

from coinexchange.btc.queue.bitcoind_agent import BitcoindAgent

class Command(BaseCommand):
    args = ''
    help = 'Bitcoind worker'

    def handle(self, *args, **options):
        agent = BitcoindAgent()
        try:
            agent.start_consuming()
        except KeyboardInterrupt:
            print "Keyboard interrupt received.  Exiting."
