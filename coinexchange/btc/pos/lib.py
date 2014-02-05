
import decimal

from coinexchange.btc.queue.bitcoind_client import BitcoindClient

from coinexchange.btc.pos.models import ReceiveAddress, SalesTransaction

class NewReceiveAddressException(Exception):
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
