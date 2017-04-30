import os
import sys
import logging
import traceback
import time

from bts2helper import *
import simplejson as json
from utils import *

try:
  tx = sys.stdin.read()
except:
  print 'invalid json'
  sys.exit(-1)

to_sign = bts2helper_tx_digest(tx, CHAIN_ID)

signature = bts2helper_sign_compact(to_sign, str(sys.argv[1]))

tx = json.loads(tx)

if not tx.get('signatures'):
  tx['signatures'] = []

tx['signatures'].append(signature)
print json.dumps(tx, indent=2)