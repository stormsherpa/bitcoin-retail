
import yaml
import uuid
import time

import pika

from django.conf import settings

_publisher_instances = dict()

class CoinexchangePublisher():
    def __init__(self, queuename):
        mqparam = pika.connection.URLParameters(settings.BITCOIN_QUEUE_URL)

        self.queue_name = queuename
        self.mqconn = pika.BlockingConnection(mqparam)
        self.channel = self.mqconn.channel()
        self.channel.queue_declare(queue=queuename,
                                   durable=True)

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(self._receive_response,
                                   no_ack=True,
                                   queue=self.callback_queue)
#         self.command = None
        self.correlation_id = None
#         self.response_body = None
        self.rpc_timeout = None
        self.rpc_timeout_interval = 5 #BITCOIN_QUEUE.get('rpc_timeout', 5)
        self.last_healthcheck = int(time.time())

        instances = _publisher_instances.get(queuename, list())
        instances.append(self)
        _publisher_instances[queuename] = instances

    @classmethod
    def get_instance(cls, queuename):
        instances = _publisher_instances.get(queuename, list())
        _publisher_instances[queuename] = [x for x in instances if x._healthcheck()]
#         if _publisher_instances[queuename]:
        for ci in _publisher_instances[queuename]:
            return ci
        return cls(queuename)

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

    def _receive_response(self, ch, method, props, body):
        print "Got response:\n===%s\n===" % body
        if self.correlation_id == props.correlation_id:
            self.response_body = body

    def send(self, body):
        return self.channel.basic_publish(exchange='',
                                          routing_key=self.queue_name,
                                          mandatory=True,
                                          body = body)


class CoinexchangeWorker():
    def __init__(self, queuename, handler):
        mqparam = pika.connection.URLParameters(settings.BITCOIN_QUEUE_URL)
        print settings.BITCOIN_QUEUE_URL
        self.mqconn = pika.BlockingConnection(mqparam)
        self.channel = self.mqconn.channel()
        self.channel.queue_declare(queue=queuename,
                                   durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.queue_name = queuename
        self.lastget = None
        self.channel.basic_consume(handler, queue=queuename)

    def start_consuming(self):
        print "Starting..."
        self.channel.start_consuming()