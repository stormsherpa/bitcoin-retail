
import os
import sys
import yaml

_config = {'BITCOINRPC_ARGS':{'args':['bitcoin', 'R7q2heIYxi'],
                         'kwargs': {'port': 8321}},
           'BITCOIN_QUEUE':
                {'url': 'amqp://coinexchange:coinexchange@jenkins.stormsherpa.com:5672/coinexchange',
                }
           }

_running_config = dict()
_running_config.update(_config)

_config_yaml_file = os.environ.get("COINEXCHANGE_CONFIG", None)
if _config_yaml_file:
    try:
        with open(_config_yaml_file, 'r') as yaml_file:
            _yaml_config = yaml.load(yaml_file.read())
        _running_config.update(_yaml_config)
    except IOError as e:
        print "Error opening config yaml."
        raise e

for conf_name in _running_config.keys():
    setattr(sys.modules[__name__], conf_name, _running_config[conf_name])
