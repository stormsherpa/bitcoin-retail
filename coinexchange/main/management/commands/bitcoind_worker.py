
from django.core.management.base import BaseCommand, CommandError

from coinexchange.btc.queue.bitcoind_agent import BitcoindAgent

class Command(BaseCommand):
    args = ''
    help = 'Bitcoind worker'
    
    def handle(self, *args, **options):
        agent = BitcoindAgent()
        agent.start_consuming()
