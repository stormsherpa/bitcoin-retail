
import decimal

from coinexchange.btc.queue.bitcoind_client import BitcoindClient

from coinexchange.btc.pos.models import ReceiveAddress, SalesTransaction

def get_available_receive_address(merchant):
    try:
        return merchant.pos_receive_address.filter(available=True)[0]
    except ReceiveAddress.DoesNotExist:
        pass
    addr = BitcoindClient.get_instance().getnewaddress(merchant.btc_account)
    print "Address: addr"
    new_addr = ReceiveAddress(merchant=merchant, address=addr, available=True)
    new_addr.save()
    return new_addr
