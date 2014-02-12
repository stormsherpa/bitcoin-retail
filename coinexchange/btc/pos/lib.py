
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
    btc_url = "bitcoin:%s?amount=%0.8f" % (receive_address.address, btc_amount)
    sale = SalesTransaction(merchant=merchant,
                            reference=reference,
                            amount=amount,
                            currency=merchant.currency,
                            currency_btc_exchange_rate=exchange_rate,
                            btc_amount=btc_amount,
                            btc_address=receive_address,
                            btc_request_url=btc_url)
    sale.save()
    return sale

def sale_json(sale):
    response = {
            'reference': sale.reference,
            'sale_id': sale.id,
            'address': sale.btc_address.address,
            'currency': sale.currency,
            'fiat_amount': "%0.2f" % sale.amount,
            'btc_amount': "%0.8f" % sale.btc_amount,
            'btc_request_url': sale.btc_request_url,
            'pending': bool(not sale.btc_txid),
            }
    return response
