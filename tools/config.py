#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import ConfigParser
import sys
import os
reload(sys)
sys.setdefaultencoding('utf-8')
configFile = os.path.expanduser('~/.qingcloud/config.ini')
ini = ConfigParser.ConfigParser()

ini.read(configFile)
instances = ini.get('opt', 'instances')
keypair = ini.get('opt', 'keypair')
zone = ini.get('opt', 'zone')
image_name = "redis-base-demo"
key = ini.get('key', 'key')
secret = ini.get('key', 'secret')
