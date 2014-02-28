
import json
import requests
import time
import datetime

from django.utils.timezone import utc

from coinexchange.settings import COINBASE_API

COINBASE_PERMS = 'balance+addresses+sell+transfers'
TOKEN_URL = "https://coinbase.com/oauth/token"

class TokenRefreshException(Exception):
    pass

def get_access_token(creds):
    if creds.access_token and creds.access_token_expire_time:
        utcnow = datetime.datetime.utcnow().replace(tzinfo=utc)
        if utcnow < creds.access_token_expire_time:
            return creds.access_token
    if creds.refresh_token:
        raise TokenRefreshException("Refreshing token is not yet supported.")
    elif creds.code and not creds.refresh_token:
        args = {'grant_type': 'authorization_code',
                'code': creds.code,
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
            creds.access_token_expire_time = datetime.datetime.fromtimestamp(expire_time, utc)
            creds.token_response = json.dumps(rjson)
            creds.save()
            return creds.access_token
    else:
        raise TokenRefreshException("Could not get coinbase access token.  Unexpected state: ApiCreds.id=%s" % creds.id)
