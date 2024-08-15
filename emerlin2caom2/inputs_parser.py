import os
import logging
import sys

from ast import literal_eval
import configparser


logger = logging.getLogger('logger')


def read_inputs(inputs_file):
    if not os.path.isfile(inputs_file):
        logger.critical('inputs file: {} not found'.format(inputs_file))
        sys.exit()
    config_raw = configparser.RawConfigParser()
    config_raw.read(inputs_file)
    config = config_raw._sections
    print(config.keys())
    for key in config.keys():
        for key2 in config[key].keys():
            try:
                config[key][key2] = literal_eval(config[key][key2])
            except ValueError:
                pass
            except SyntaxError:
                pass
    inputs = config['inputs']
    for key, value in inputs.items():
        logger.info('{0:10s}: {1}'.format(key, value))
    return config['inputs']


conf_file = '/home/h14471mj/e-merlin/casa6_docker/prod/TS8004_C_001_20190801/inputs.ini'

inputs = read_inputs(conf_file)
print(inputs)
