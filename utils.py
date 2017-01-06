import os
from decimal import Decimal

ACCOUNT_PREFIX   = 'moneda-par.'

DB_URL           = os.environ.get('DB_URL', 'mysql+pymysql://root:248@127.0.0.1/par')
REGISTER_PRIVKEY = os.environ.get('REGISTER_PRIVKEY', '')

CORE_ASSET       = '1.3.0'

ASSET_PRECISION  = 100

ASSET_ID         = '1.3.1236'
GOBIERO_PAR_ID   = '1.2.150830'
PROPUESTA_PAR_ID = '1.2.151476'

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
