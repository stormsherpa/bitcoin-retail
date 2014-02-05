
import time

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    args = ''
    help = 'Poll for Transactions'

    def handle(self, *args, **options):
        try:
            while True:
                print "Checking..."
                time.sleep(10)
        except KeyboardInterrupt:
            print "Keyboard interrupt received.  Exiting."