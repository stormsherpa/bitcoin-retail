
import decimal
import json

import requests

from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc.pos.models import ReceiveAddress, SalesTransaction

class NewReceiveAddressException(Exception):
    pass

class ExchangeRateException(Exception):
    pass

def get_available_receive_address(merchant):
    try:
        return merchant.pos_receive_address.filter(available=True)[0]
    except IndexError:
        pass
    r = BitcoindClient.get_instance().getnewaddress(merchant.btc_account)
    if r.get('error', True):
        raise NewReceiveAddressException()
    addr = r.get('result')
    print "Returning addr: %s" % addr
    new_addr = ReceiveAddress(merchant=merchant, address=addr, available=True)
    new_addr.save()
    return new_addr

def get_exchange_rate(currency):
    r = requests.get("https://coinbase.com/api/v1/prices/spot_rate", data={'currency':currency})
    if r.status_code == 200:
        data = json.loads(r.text)
        return decimal.Decimal(data.get('amount'))
    raise ExchangeRateException()

def make_new_sale(merchant, fiat_amount, reference):
    exchange_rate = get_exchange_rate(merchant.currency)
    amount = decimal.Decimal(fiat_amount)
    btc_amount = amount/exchange_rate
    receive_address = get_available_receive_address(merchant)
    sale = SalesTransaction(merchant=merchant,
                            reference=reference,
                            amount=amount,
                            currency=merchant.currency,
                            currency_btc_exchange_rate=exchange_rate,
                            btc_amount=btc_amount,
                            btc_address=receive_address)
    sale.save()
    return sale
