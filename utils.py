import os
from decimal import Decimal, ROUND_UP
import rpc
import os
homedir = os.environ['HOME']

ACCOUNT_PREFIX   = 'discoin.'

# PRIVATE NETWORK -> ssh -i bitshares_fork_1.pem ubuntu@35.163.59.126
# CHAIN_ID = 'bde617520673d18e67db5d7060ca2740f80e28093519c30176044c8d4a227e73'

# PRIVATE NETWORK -> tuti localhost
# CHAIN_ID = 'f5a42a1c16cf678773313f5f94ef7ebb69257c5f33a147aa8c4ac0fa5e451805'

# PRIVATE NETWORK -> MAIN NETWORK
# CHAIN_ID = '4018d7844c78f6a6c41c6a552b898022310fc5dec06da467ee7905a8dad512c8';

CHAIN_ID              = 'bde617520673d18e67db5d7060ca2740f80e28093519c30176044c8d4a227e73'
DB_URL                = os.environ.get('DB_URL', 'mysql+pymysql://root:248@127.0.0.1/discoin?charset=utf8')
REGISTER_PRIVKEY      = os.environ.get('REGISTER_PRIVKEY', '5JQGCnJCDyraociQmhDRDxzNFCd8WdcJ4BAj8q1YDZtVpk5NDw9')

CORE_ASSET            = '1.3.0'
ASSET_PRECISION       = 100

DISCOIN_ADMIN_ID      = '1.2.18'     # discoin.admin
DISCOIN_ADMIN_NAME    = 'discoin.admin'
ASSET_ID              = '1.3.2'
DISCOIN_ID            = ASSET_ID
DISCOIN_CREDIT_ID     = '1.3.3' # DESCUBIERTO | THEDISCOIN.OD
DISCOIN_ACCESS_ID     = '1.3.4' # ENDORSEMENT | DISCOIN.KEY | THEDISCOIN.A
DISCOIN_SYMBOL        = 'THEDISCOIN.M'
DISCOIN_CREDIT_SYMBOL = 'THEDISCOIN.OD'
DISCOIN_ACCESS_SYMBOL = 'THEDISCOIN.A'

if homedir=='/home/tuti':
  CHAIN_ID              = 'f5a42a1c16cf678773313f5f94ef7ebb69257c5f33a147aa8c4ac0fa5e451805'
  DB_URL                = os.environ.get('DB_URL', 'mysql+pymysql://root:248@127.0.0.1/discoin?charset=utf8')
  REGISTER_PRIVKEY      = os.environ.get('REGISTER_PRIVKEY', '5KU1QuhwwoJ5mJJuCgMXzXJx8FmhQvnPAfGgu7STJbPazUYxwHT')
  DISCOIN_ADMIN_ID      = '1.2.22'     # discoin.admin
  DISCOIN_ADMIN_NAME    = 'discoin-gov'
  ASSET_ID              = '1.3.10' #'1.3.7'
  DISCOIN_ID            = ASSET_ID
  DISCOIN_CREDIT_ID     = '1.3.8' # DESCUBIERTO | THEDISCOIN.OD
  DISCOIN_ACCESS_ID     = '1.3.9' # ENDORSEMENT | DISCOIN.KEY | THEDISCOIN.A
  DISCOIN_SYMBOL        = 'DISCOIN' #'DISCOINASSET'
  DISCOIN_CREDIT_SYMBOL = 'DISCOINOVERDRAFT'
  DISCOIN_ACCESS_SYMBOL = 'DISCOINENDORSE'

if str(os.environ.get('PROD', '0')) == '1':
  CHAIN_ID              = '4018d7844c78f6a6c41c6a552b898022310fc5dec06da467ee7905a8dad512c8';
  DB_URL                = os.environ.get('DB_URL', "mysql+pymysql://discoin:7rc)FE#'r6=rus~M@discoin-db-cluster.cluster-cmhexratphp1.us-west-2.rds.amazonaws.com/discoin?charset=utf8")
  REGISTER_PRIVKEY      = os.environ.get('REGISTER_PRIVKEY', '')
  DISCOIN_ADMIN_ID      = '1.2.1105469'
  DISCOIN_ADMIN_NAME    = 'discoin-gov'
  ASSET_ID              = '1.3.4679'#'1.3.4621'
  DISCOIN_ID            = ASSET_ID
  DISCOIN_CREDIT_ID     = '1.3.4622' # DESCUBIERTO | THEDISCOIN.OD
  DISCOIN_ACCESS_ID     = '1.3.4623' # ENDORSEMENT | DISCOIN.KEY | THEDISCOIN.A
  DISCOIN_SYMBOL        = 'DISCOIN.AR'
  DISCOIN_CREDIT_SYMBOL = 'DISCOIN.IBALANCE'
  DISCOIN_ACCESS_SYMBOL = 'DISCOIN.ENDORSE'

ALL_TRACKED_ASSETS  = [DISCOIN_ID, DISCOIN_CREDIT_ID, DISCOIN_ACCESS_ID]
ALL_VALID_ASSETS    = [DISCOIN_ID, DISCOIN_ACCESS_ID]

print ('-----using:', REGISTER_PRIVKEY)
print ('-----chain_id:', CHAIN_ID)
print ('-----asset', DISCOIN_SYMBOL)

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
  
def decode_memo(memo_message, _amount, asset):
  import hashlib, binascii
  
  refund_prefix    = binascii.hexlify('~re:'.encode()).decode('utf-8')
  discount_prefix  = binascii.hexlify('~di:'.encode()).decode('utf-8')
  _type = ''
  if memo_message:  
    if memo_message[:8]==refund_prefix:
      _type = 'refund' 
    if memo_message[:8]==discount_prefix:
      _type = 'discount' 
    if _type=='':
      return {
        '_type'       : 'transfer',
        'bill_id'     : 0,
        'bill_amount' : 0,
        'discount'    : 0,
        'memo'        : ''
      }
  if memo_message is None or memo_message=='None':
     #print('--- MEMO IS:', memo_message)   
    return {
        '_type'       : 'transfer',
        'bill_id'     : 0,
        'bill_amount' : 0,
        'discount'    : 0,
        'memo'        : ''
      }
  _memo = binascii.unhexlify(memo_message).decode('utf-8')
  _memo_split = _memo.split(':')
  bill_id     = '' 
  bill_amount = 0
  if len(_memo_split)>2:
    # ~re:1500:the bill
    bill_amount = Decimal(try_float(_memo_split[1]))
    bill_id     = _memo_split[2] 
  discount = 0
  if bill_amount>0:
    discount = round_decimal(Decimal(_amount)*100/bill_amount)
  return {
    '_type'       : _type,
    'bill_id'     : bill_id,
    'bill_amount' : bill_amount,
    'discount'    : discount,
    'memo'        : _memo
  }


def convert_date(timestamp, hour_delta):
  import time
  import datetime
  
  return (timestamp+datetime.timedelta(hours = hour_delta)).strftime('%Y-%m-%dT%H:%M:%S') 
  
