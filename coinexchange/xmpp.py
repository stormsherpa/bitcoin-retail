
import requests

from django.conf import settings

domain = getattr(settings,"XMPP_DOMAIN")

def send_message(message):
    cfg = settings.XMPP
    user = cfg.get('userjid')
    passwd = cfg.get('password')
    url = "%s/message/send/xml" % cfg.get('url')
    headers={'Content-Type': 'application/xml'}
    r = requests.post(url, data=message, auth=(user,passwd), headers=headers)
#     print r.status_code

def get_userjid(user):
    return "account-id-%s@%s" % (user.id, domain)
