import os
from decimal import Decimal

ACCOUNT_PREFIX   = os.environ.get('UW_ACCOUNT_PREFIX', 'test-pesocial.')
ASSET_ID         = os.environ.get('UW_ASSET_ID', '1.3.1004')
ASSET_PRECISION  = int(os.environ.get('UW_ASSET_PRECISION', '10000'))
DB_URL           = os.environ.get('UW_DB_URL', 'mysql+pymysql://root:248@127.0.0.1/par')
GOBIERO_PAR_ID   = os.environ.get('UW_EXTRA_OWNER', '1.2.150830')
REGISTER_PRIVKEY = os.environ.get('UW_REGISTER_PRIVKEY', '')
PROPOSER_WIF     = os.environ.get('UW_PROPOSER_WIF', '')

CORE_ASSET       = '1.3.0'

BSW_REGISTER_ACCOUNT = '1.2.31489'
CHAIN_ID             = '4018d7844c78f6a6c41c6a552b898022310fc5dec06da467ee7905a8dad512c8'

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
