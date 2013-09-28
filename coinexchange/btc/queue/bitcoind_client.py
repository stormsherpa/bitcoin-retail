
import yaml
import uuid
import time

import pika

from coinexchange.btc.config import BITCOIN_QUEUE

_client_instances = list()

class BitcoindClientError(Exception):
    def __init__(self, msg, error_yaml, *args, **kwargs):
        self.error_yaml = error_yaml
        Exception.__init__(self, msg, *args, **kwargs)

class BitcoindClientTimeoutError(Exception):
    pass

class BitcoindClient():
    def __init__(self):
        mqparam = pika.connection.URLParameters(BITCOIN_QUEUE['url'])
        self.mqconn = pika.BlockingConnection(mqparam)
        self.channel = self.mqconn.channel()
        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(self._receive_response,
                                   no_ack=True,
                                   queue=self.callback_queue)
        self.command = None
        self.correlation_id = None
        self.response_body = None
        self.rpc_timeout = None
        self.rpc_timeout_interval = BITCOIN_QUEUE.get('rpc_timeout', 5)
        
        _client_instances.append(self)

    @classmethod
    def get_instance(cls):
        if _client_instances:
            for ci in _client_instances:
                # Eventually check health status
                return ci
        return cls()

    def _prep_command(self, cmd_name, *args, **kwargs):
        self.command = cmd_name
        cmd_dict = {'command': cmd_name,
                    'args': args,
                    'kwargs': kwargs}
        return yaml.dump(cmd_dict)
    
    def _send_command(self, cmd_yaml):
        self.correlation_id = str(uuid.uuid4())
        pika_properties = pika.BasicProperties(reply_to = self.callback_queue,
                                               correlation_id = self.correlation_id)
        self.channel.basic_publish(exchange='',
                                   routing_key='bitcoind_rpc',
                                   properties=pika_properties,
                                   body = cmd_yaml)
        self.rpc_timeout = int(time.time()) + self.rpc_timeout_interval

    def _receive_response(self, ch, method, props, body):
        print "Got response:\n===%s\n===" % body
        if self.correlation_id == props.correlation_id:
            self.response_body = body

    def _response_wait(self):
        while not self.response_body:
            if int(time.time()) > self.rpc_timeout:
                raise BitcoindClientTimeoutError("Timeout waiting for command %s" % self.command)
            self.mqconn.process_data_events()
        return_body = self.response_body
        # cleanup state for next round
        self.correlation_id = None
        self.response_body = None
        self.command = None
        return yaml.load(return_body)

    def getbalance(self, account):
        cmd_yaml = self._prep_command('getbalance', account)
        self._send_command(cmd_yaml)
        return self._response_wait()
    
    def getaccountaddress(self, account):
        cmd_yaml = self._prep_command('getaccountaddress', account)
        self._send_command(cmd_yaml)
        return self._response_wait()
