import os
from decimal import Decimal

ACCOUNT_PREFIX   = 'moneda-par.'

DB_URL           = os.environ.get('DB_URL', 'mysql+pymysql://root:248@127.0.0.1/par')
REGISTER_PRIVKEY = os.environ.get('REGISTER_PRIVKEY', '')

CORE_ASSET       = '1.3.0'

ASSET_PRECISION  = 100

GOBIERO_PAR_ID   = '1.2.150830'
PROPUESTA_PAR_ID = '1.2.151476'

ASSET_ID         = '1.3.1236'
MONEDAPAR_ID     = ASSET_ID
DESCUBIERTO_ID   = '1.3.1237'

AVAL_1000        = '1.3.1319'
AVAL_10000       = '1.3.1322'
AVAL_30000       = '1.3.1320'
AVAL_100000      = '1.3.1321'
ALL_AVAL_TYPES   = [AVAL_1000, AVAL_10000, AVAL_30000, AVAL_100000]

ALL_TRACKED_ASSETS = ALL_AVAL_TYPES + [MONEDAPAR_ID, DESCUBIERTO_ID]

CHAIN_ID         = '4018d7844c78f6a6c41c6a552b898022310fc5dec06da467ee7905a8dad512c8'

def ref_block(block_id):
  block_num    = block_id[0:8]
  block_prefix = block_id[8:16]
  
  ref_block_num     = int(block_num,16)
  ref_block_prefix  = int("".join(reversed([block_prefix[i:i+2] for i in range(0, len(block_prefix), 2)])),16)

  return ref_block_num, ref_block_prefix

def amount_value(amount, asset):
  d = Decimal(amount)/Decimal(10**asset['precision'])
  return str(d)

def object_id(obj_id):
  return int(obj_id.split('.')[-1])

def real_name(name):
  if name.startswith(ACCOUNT_PREFIX):
    name = name[len(ACCOUNT_PREFIX):]
  return name

def filter_upper(chain):
  ret = chain.upper()
  return ret if ret else chain

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")
