
import time
import json

from django.core.management.base import BaseCommand, CommandError
from django.template import Context, loader
from django.utils.safestring import mark_safe

from coinexchange.btc.pos.models import SalesTransaction
from coinexchange import xmpp

class Command(BaseCommand):
    args = ''
    help = 'Poll for Transactions'

    def handle(self, *args, **options):
        t = loader.get_template("coinexchange/xmpp/pos_confirm.xml")
        for tx in SalesTransaction.objects.all():
            print "%s - %s" % (tx.id, tx.merchant.user.username)
            print xmpp.get_userjid(tx.merchant.user)
            body = {'sale_id': tx.id,
                    'status': 'confirmed'}
            c = Context({'tx': tx,
                         'json_body': mark_safe(json.dumps(body)),
                         'to': xmpp.get_userjid(tx.merchant.user)})
            print t.render(c)
            xmpp.send_message(t.render(c))
            
