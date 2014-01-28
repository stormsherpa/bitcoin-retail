#!/usr/bin/python
import sys, logging, struct, hashlib
from struct import *

auth_shared_secret="coinExchange"

sys.stderr = open('/opt/fork21/var/log/ejabberd/extauth_err.log', 'a')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/opt/fork21/var/log/ejabberd/extauth.log',
                    filemode='a')

logging.info('extauth script started, waiting for ejabberd requests')
class EjabberdInputError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
########################################################################
#Declarations
########################################################################
def ejabberd_in():
        logging.debug("trying to read 2 bytes from ejabberd:")
        try:
            input_length = sys.stdin.read(2)
        except IOError:
            logging.debug("ioerror")
        if len(input_length) is not 2:
            logging.debug("ejabberd sent us wrong things!")
            raise EjabberdInputError('Wrong input from ejabberd!')
        logging.debug('got 2 bytes via stdin: %s'%input_length)
        (size,) = unpack('>h', input_length)
        logging.debug('size of data: %i'%size)
        income=sys.stdin.read(size).split(':')
        logging.debug("incoming data: %s"%income)
        return income
def ejabberd_out(bool):
        logging.debug("Ejabberd gets: %s" % bool)
        token = genanswer(bool)
        logging.debug("sent bytes: %#x %#x %#x %#x" % (ord(token[0]), ord(token[1]), ord(token[2]), ord(token[3])))
        sys.stdout.write(token)
        sys.stdout.flush()
def genanswer(bool):
        answer = 0
        if bool:
            answer = 1
        token = pack('>hh', 2, answer)
        return token
def auth(in_user, in_host, password):
    passwd_in_str="%s@%s:%s" % (in_user, in_host, auth_shared_secret)
    passwd_str=hashlib.md5(passwd_in_str).hexdigest()
    logging.debug("Passwd: %s -> %s" % (passwd_in_str, passwd_str))
    out=False #defaut to O preventing mistake
    if passwd_str==password:
        out=True
    else:
        logging.info("Wrong password for user: %s.  Expected: '%s' Got: '%s'"%(in_user, passwd_str, password))
        out=False
    return out
def log_result(op, in_user, bool):
    if bool:
        logging.info("%s successful for %s"%(op, in_user))
    else:
        logging.info("%s unsuccessful for %s"%(op, in_user))
########################################################################
#Main Loop
########################################################################
while True:
    logging.debug("start of infinite loop")
    try: 
        ejab_request = ejabberd_in()
    except EjabberdInputError, inst:
        logging.info("Exception occured: %s", inst)
        break
    logging.debug('operation: %s'%(ejab_request[0]))
    op_result = False
    if ejab_request[0] == "auth":
        op_result = auth(ejab_request[1], ejab_request[2], ejab_request[3])
        ejabberd_out(op_result)
        log_result(ejab_request[0], ejab_request[1], op_result)
    elif ejab_request[0] == "isuser":
        ejabberd_out(True)
        #log_result(ejab_request[0], ejab_request[1], op_result)
    elif ejab_request[0] == "setpass":
        op_result=False
        ejabberd_out(op_result)
        log_result(ejab_request[0], ejab_request[1], op_result)
logging.debug("end of infinite loop")
logging.info('extauth script terminating')
