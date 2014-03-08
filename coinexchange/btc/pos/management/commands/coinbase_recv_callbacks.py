
import sys
import time
import datetime
import json
import yaml
import traceback
# import objgraph

from django.core.management.base import BaseCommand, CommandError


from coinexchange.btc.models import CoinTxnLog, CoinExchangeUser

from coinexchange.btc.pos.models import PaymentNotification, UnexpectedPaymentNotification, SalesTransaction
from coinexchange.btc.pos import lib
from coinexchange.btc.queue import CoinexchangeWorker

def my_handler(ch, method, properties, body):
    print body
    try:
        data = json.loads(body)
    except ValueError as e:
        print "There was an error decoding json: %s: %s" % (e.__class__, e)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return
    payment = PaymentNotification(body)
    print "Payment notification: %s" % payment
    result = lib.process_coinbase_payment_notification(payment)
    
    if isinstance(result, SalesTransaction):
        print "Sales transaction updated: %s" % result.id
        lib.notify_transaction(result, 'confirmed')
    elif isinstance(result, UnexpectedPaymentNotification):
        print "Unexpected notification: %s" % result.id
    else:
        print "Unexpected notification state! %s" % result 
    ack = ch.basic_ack(delivery_tag=method.delivery_tag)

class Command(BaseCommand):
    args = ''
    help = 'Poll for Transactions'

    def handle(self, *args, **options):
        worker = CoinexchangeWorker('coinbase_receive_callback', my_handler)
        try:
            worker.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print "%s: %s" % (e.__class__, e)
            traceback.print_exc()
