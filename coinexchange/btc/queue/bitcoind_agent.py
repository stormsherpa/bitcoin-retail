
import yaml

import pika
import bitcoinrpc

from coinexchange.btc.config import BITCOINRPC_ARGS
from coinexchange.btc.config import BITCOIN_QUEUE


class BitcoindAgent():
    def __init__(self):
        self.rpcconn = bitcoinrpc.connect_to_remote(*BITCOINRPC_ARGS['args'],
                                                    **BITCOINRPC_ARGS['kwargs'])
        mqparam = pika.connection.URLParameters(BITCOIN_QUEUE['url'])
        self.mqconn = pika.BlockingConnection(mqparam)
        self.channel = self.mqconn.channel()
        self.channel.queue_declare(queue='bitcoind_rpc',
                                   durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self._rpc_callback, queue='bitcoind_rpc')

    def start_consuming(self):
        self.channel.start_consuming()

    rpc_passthru_commands = ['getaccountaddress',
                             'listaccounts',
                             'getbalance',
                            ]

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
                rpc_result = {'result': {'error_string': e, 'error_type': e.__class__},
                              'error': True}
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
