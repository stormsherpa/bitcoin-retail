
import json
import requests
import time
import datetime
import traceback

from django.utils.timezone import utc

from coinbase import CoinbaseAccount

from coinexchange.settings import COINBASE_API
from coinexchange.coinbase.models import ApiCreds

COINBASE_PERMS = 'balance+addresses+sell+transfers+transactions'
TOKEN_URL = "https://coinbase.com/oauth/token"

class TokenRefreshException(Exception):
    pass

class InvalidAccountException(Exception):
    pass

def get_access_token(creds, code=None):
    if code:
        args = {'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': COINBASE_API.get('redirect_uri'),
                'client_id': COINBASE_API.get('client_id'),
                'client_secret': COINBASE_API.get('client_secret'),
                }
        r = requests.post(TOKEN_URL, data=args)
        if r.status_code == requests.codes.ok:
            rjson = r.json()
            creds.refresh_token = rjson.get('refresh_token')
            creds.access_token = rjson.get('access_token')
            expire_time = int(time.time()) + rjson.get('expires_in', 0)
            expire_time -= 60
            creds.access_token_expire_time = datetime.datetime.fromtimestamp(expire_time, utc)
            creds.token_response = json.dumps(rjson)
            creds.save()
            return creds.access_token
    if creds.access_token and creds.access_token_expire_time:
        utcnow = datetime.datetime.utcnow().replace(tzinfo=utc)
        if utcnow < creds.access_token_expire_time:
#             print "Using existing access_token: %s" % creds.access_token
            print "Using existing access token."
            return creds.access_token
    if creds.refresh_token:
        old_token = json.loads(creds.token_response)
        args = {'grant_type': 'refresh_token',
                'refresh_token': old_token.get('refresh_token'),
                'redirect_uri': COINBASE_API.get('redirect_uri'),
                'client_id': COINBASE_API.get('client_id'),
                'client_secret': COINBASE_API.get('client_secret'),
                }
        r = requests.post(TOKEN_URL, data=args)
        if r.status_code == requests.codes.ok:
            rjson = r.json()
            creds.access_token = rjson.get('access_token')
            creds.refresh_token = rjson.get('refresh_token')
            expire_time = int(time.time()) + rjson.get('expires_in', 0)
            expire_time -= 60
            creds.access_token_expire_time = datetime.datetime.fromtimestamp(expire_time, utc)
            creds.token_response = json.dumps(rjson)
            creds.save()
            return creds.access_token
        else:
            print "Error refreshing token: %s" % r.status_code
            print r.text
            raise TokenRefreshException("Could not refresh access token from coinbase")
    else:
        raise TokenRefreshException("Could not get coinbase access token.  Unexpected state: ApiCreds.id=%s" % creds.id)

def get_api_instance(merchant):
    creds = ApiCreds.load_by_merchant(merchant)
    access_token = get_access_token(creds)
#     print creds.token_response
#     print "Getting coinbase api instance with access_token: %s" % access_token
    if creds.token_response:
        try:
            return CoinbaseAccount(oauth_access_token=access_token)
        except Exception as e:
            traceback.print_exc()
            print "Coinbase account exception: %s %s" % (e.__class__, e)
    msg = "No token response object in merchant's api creds. Merchant user id: %s" % merchant.user.id
    raise InvalidAccountException(msg)

# def get_addresses(access_token):
#     return access_token.

# def get_transactions(access_token):
#     req_args = {'access_token': access_token}
#     r = requests.get("https://coinbase.com/api/v1/transactions", data=req_args)
#     if r.status_code == requests.codes.ok:
#         rjson = r.json()
#         return rjson
#     print r.status_code

def get_account_info(coinbase_api):
    acct_info = dict()
#     rjson = get_addresses(access_token)
    acct_info['receive_address'] = coinbase_api.receive_address
#     acct_info['transactions'] = get_transactions(access_token)
    return acct_info
