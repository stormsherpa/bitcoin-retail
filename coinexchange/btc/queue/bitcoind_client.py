
import yaml
import uuid
import time

import pika

from django.conf import settings

_client_instances = list()

class BitcoindClientError(Exception):
    def __init__(self, msg, error_yaml, *args, **kwargs):
        self.error_yaml = error_yaml
        Exception.__init__(self, msg, *args, **kwargs)

class BitcoindClientTimeoutError(Exception):
    pass

class BitcoindClient():
    def __init__(self):
        mqparam = pika.connection.URLParameters(settings.get("BITCOIN_QUEUE_URL"))
        
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
        self.last_healthcheck = int(time.time())
        
        _client_instances.append(self)

    @classmethod
    def get_instance(cls):
        _client_instances[:] = [x for x in _client_instances if x._healthcheck()]
        if _client_instances:
            for ci in _client_instances:
                return ci
        return cls()

    def _healthcheck(self):
        now = int(time.time())
        if now < (self.last_healthcheck+30):
            print "skipping health check"
            return True
        self.last_healthcheck = now
        try:
            self.correlation_id = str(uuid.uuid4())
            props = pika.BasicProperties(correlation_id = self.correlation_id)
            self.channel.basic_publish(exchange='',
                                       routing_key=self.callback_queue,
                                       properties = props,
                                       body='test')
            self.rpc_timeout = int(time.time()) + 1
            resp = self._response_wait()
            if resp=='test':
                print "%s pass healthcheck" % self
                return True
        except Exception as e:
            print e
        print "%s failing healthcheck." % self
        return False

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

    def getaddressesbyaccount(self, account):
        cmd_yaml = self._prep_command('getaddressesbyaccount', account)
        self._send_command(cmd_yaml)
        return self._response_wait()

    def getnewaddress(self, account):
        cmd_yaml = self._prep_command('getnewaddress', account)
        self._send_command(cmd_yaml)
        return self._response_wait()

    def user_withdrawl(self, request):
        self._send_command(request.as_yaml())
        return self._response_wait()

    def rescan_transactions(self, account):
        cmd_yaml = self._prep_command('rescan_transactions', account)
        self._send_command(cmd_yaml)
        return self._response_wait()
