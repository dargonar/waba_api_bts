import os
from decimal import Decimal, ROUND_UP
import rpc

# ACCOUNT_PREFIX   = 'moneda-par.'

ACCOUNT_PREFIX   = 'discoin.'

DB_URL            = os.environ.get('DB_URL', 'mysql+pymysql://root:248@127.0.0.1/discoin?charset=utf8')
REGISTER_PRIVKEY  = os.environ.get('REGISTER_PRIVKEY', '5JQGCnJCDyraociQmhDRDxzNFCd8WdcJ4BAj8q1YDZtVpk5NDw9')
# LOCKSMITH_PRIVKEY = os.environ.get('LOCKSMITH_PRIVKEY', '5KjQfg8uVMw3g72LLbTd9e6XPqzzy6Zo39NsbUKfEk9WNiYjqur')
LOCKSMITH_PRIVKEY = os.environ.get('LOCKSMITH_PRIVKEY', '5JMkKXKcLbbrH4ypQ1Z2pP2qKtL9r3nsLycht6UsDxYu9KoKMD9')

DISCOIN_ADMIN_ID     = '1.2.18'     # discoin.admin
DISCOIN_ADMIN_NAME   = 'discoin.admin'
# DISCOIN_LOCKSMITH_ID = '1.2.24'   # discoin.locksmith 
DISCOIN_LOCKSMITH_ID = '1.2.17'     # nathan
DISCOIN_HANDLER_ID   = '1.2.23'     # discoin.handler

CORE_ASSET       = '1.3.0'

ASSET_PRECISION  = 100


# GOBIERO_PAR_ID   = '1.2.150830'
# PROPUESTA_PAR_ID = '1.2.151476'

ASSET_ID            = '1.3.9'
DISCOIN_ID          = ASSET_ID
DISCOIN_CREDIT_ID   = '1.3.7' # DESCUBIERTO | THEDISCOIN.OD
DISCOIN_ACCESS_ID   = '1.3.8' # ENDORSEMENT | DISCOIN.KEY | THEDISCOIN.A


DISCOIN_SYMBOL        = 'THEDISCOIN.M'
DISCOIN_CREDIT_SYMBOL = 'THEDISCOIN.OD'
DISCOIN_ACCESS_SYMBOL = 'THEDISCOIN.A'

ASSET_ID         = '1.3.1236'
MONEDAPAR_ID     = ASSET_ID
DESCUBIERTO_ID   = '1.3.1237'

# AVAL_1000        = '1.3.1319'
# AVAL_10000       = '1.3.1322'
# AVAL_30000       = '1.3.1320'
# AVAL_100000      = '1.3.1321'
# ALL_AVAL_TYPES   = [AVAL_1000, AVAL_10000, AVAL_30000, AVAL_100000]

# ALL_TRACKED_ASSETS = ALL_AVAL_TYPES + [MONEDAPAR_ID, DESCUBIERTO_ID]
# ALL_VALID_ASSETS   = ALL_AVAL_TYPES + [MONEDAPAR_ID]

ALL_TRACKED_ASSETS  = [DISCOIN_ID, DISCOIN_CREDIT_ID, DISCOIN_ACCESS_ID]
ALL_VALID_ASSETS    = [DISCOIN_ID, DISCOIN_ACCESS_ID]
CHAIN_ID         = '2cfcf449d44f477bc8415666766d2258aa502240cb29d290c1b0de91e756c559'

def ref_block(block_id):
  block_num    = block_id[0:8]
  block_prefix = block_id[8:16]
  
  ref_block_num     = int(block_num,16)
  ref_block_prefix  = int("".join(reversed([block_prefix[i:i+2] for i in range(0, len(block_prefix), 2)])),16)

  return ref_block_num, ref_block_prefix

def amount_value(amount, asset):
  d = Decimal(amount)/Decimal(10**asset['precision'])
  return str(d)

def reverse_amount_value(amount, asset):
  d = Decimal(amount)*Decimal(10**asset['precision'])
  return str(d)

def round_decimal(value):
  if not value:
    return Decimal('0')
  return value.quantize(Decimal('0.01'), rounding=ROUND_UP)

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

def is_number(s):
  try:
      float(s)
      return True
  except ValueError:
      return False
      
def try_int(value, default=0):
  try:
    return int(value)
  except:
    return default

def try_float(value, default=0.0):
  try:
    return float(value)
  except:
    return float(default)
