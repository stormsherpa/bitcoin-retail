
from coinexchange.btc.queue.bitcoind_client import BitcoindClient

def get_user_address(exchange_user, save_if_found=True):
    if not exchange_user.btc_address:
        response = BitcoindClient.get_instance().getaccountaddress(exchange_user.btc_account)
        if not response.get('error', True):
            exchange_user.btc_address = response.get('result', None)
            if save_if_found:
                exchange_user.save()
    return exchange_user.btc_address

def get_user_balance(exchange_user):
    response = BitcoindClient.get_instance().getbalance(exchange_user.btc_account)
    return response.get('result', None)


