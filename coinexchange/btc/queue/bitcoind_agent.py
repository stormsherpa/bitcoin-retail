
import yaml

import pika
import bitcoinrpc

from django.conf import settings
from django.db import transaction

from coinexchange.btc import agentlib

BITCOINRPC_ARGS = settings.BITCOINRPC_ARGS

class BitcoindAgent():
    def __init__(self):
        self.rpcconn = bitcoinrpc.connect_to_remote(*BITCOINRPC_ARGS['args'],
                                                    **BITCOINRPC_ARGS['kwargs'])
        mqparam = pika.connection.URLParameters(settings.BITCOIN_QUEUE_URL)
        print settings.BITCOIN_QUEUE_URL
        self.mqconn = pika.BlockingConnection(mqparam)
        self.channel = self.mqconn.channel()
        self.channel.queue_declare(queue='bitcoind_rpc',
                                   durable=True)
#         self.channel.queue_declare(queue='bitcoind_cast',
#                                    durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self._rpc_callback, queue='bitcoind_rpc')
#         self.channel.basic_consume(self._cast_callback, queue='bitcoind_cast')

    def start_consuming(self):
        print "Starting..."
        self.channel.start_consuming()

    rpc_passthru_commands = ['getaccountaddress',
                             'listaccounts',
                             'getbalance',
                             'getaddressesbyaccount',
                             'getnewaddress',
                             'gettransaction',
                            ]

#     def _cast_callback(self, ch, method, properties, body):
#         print "cast callback: %s" % body
#         yaml_body = yaml.load(body)
#         command = yaml_body.get('command', None)
#         if not command:
#             print "Message received without a command."
#             return
#         print "Unknown command: %s" % command


    def _rpc_callback(self, ch, method, properties, body):
        yaml_body = yaml.load(body)
        print yaml_body
        command = yaml_body.get('command', None)
        print "Got command: %s" % command

        if command in self.rpc_passthru_commands:
            rpc_args = yaml_body.get('args', list())
            rpc_kwargs = yaml_body.get('kwargs', dict())
            try:
                rpc_result = {'result': getattr(self.rpcconn, command)(*rpc_args, **rpc_kwargs),
                              'error': False}
            except Exception as e:
                print command
                print e
                rpc_result = {'result': {'error_string': e, 'error_type': e.__class__},
                              'error': True}
        elif command == "user_withdrawl":
            address = yaml_body.get('to_address', False)
            address_validation = self.rpcconn.validateaddress(address)
            account_name = yaml_body.get('account', False)
            amount = yaml_body.get('amount', 0)
            if self.rpcconn.getbalance(account_name) >= amount:
                if address_validation.isvalid:
                    send_result = self.rpcconn.sendfrom(account_name,
                                                        address_validation.address,
                                                        float(amount),
                                                        minconf=5)
                    rpc_result = {'result': 'Withdrawl processed',
                                  'txid': send_result,
                                  'error': False}
                else:
                    rpc_result = {'result': 'Invalid address',
                                  'error': True}
            else:
                rpc_result = {'result': 'Insufficient funds',
                              'error': True}
        elif command == "rescan_transactions":
            rpc_args = yaml_body.get('args', list())
            if len(rpc_args) > 0:
                account_name = rpc_args[0]
                print "rescan_transactions for %s" % account_name
                newest_move = 0
                for tx in self.rpcconn.listtransactions(account_name):
                    print tx
                    if tx.category=='move' and tx.time > newest_move:
                        print "store tx"
                        rtx = agentlib.store_btc_tx(tx)
                        print "after store tx"
                        newest_move = tx.time
                rpc_result = {'result': newest_move,
                              'error': newest_move == 0}
            else:
                rpc_result = {'result': None,
                              'error': True}
        elif command == "send_all_tx_inputs":
            rpc_args = yaml_body.get('args', list())
            rpc_result = self.send_all_tx_inputs(*rpc_args)
        else:
            rpc_result = {'result': 'unknown rpc command',
                          'error': True}

        rpc_yaml_result = yaml.dump(rpc_result)
        print "Result-body:\n===\n%s\n====" % rpc_yaml_result
        print "Reply-to: %s" % properties.reply_to
        print "correlation_id: %s" % properties.correlation_id
        ch.basic_publish(exchange='',
                         routing_key=properties.reply_to,
                         properties=pika.BasicProperties(correlation_id = properties.correlation_id),
                         body = rpc_yaml_result)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    @transaction.commit_manually
    def send_all_tx_inputs(self, txid_in, to_addr):
        try:
            if not txid_in:
                return {'result': None,
                        'error': False}
            batch = agentlib.create_batch_record(txid_in, to_addr)
            newtx = agentlib.send_all_tx_inputs(self.rpcconn, txid_in, to_addr)
            batch.txid = newtx.get('txid')
            batch.btc_tx_fee = newtx.get('tx_fee')
            batch.save()
            transaction.commit()
            return {'result': {'batch_id': batch.id,
                               'txid': newtx.get('txid')},
                    'error': False}
        except Exception as e:
            print "send_all_tx_inputs exception: %s" % e
            transaction.rollback()
            return {'result': None,
                    'error': True}
