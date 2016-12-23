import os
from decimal import Decimal

ACCOUNT_PREFIX = os.environ.get('UW_ACCOUNT_PREFIX', 'test-pesocial.')
ASSET_ID       = os.environ.get('UW_ASSET_ID', '1.3.1004')
DB_URL         = os.environ.get('UW_DB_URL', 'mysql+pymysql://root:248@127.0.0.1/par')

def amount_value(amount, asset):
  d = Decimal(amount)/Decimal(10**asset['precision'])
  return str(d)

def real_name(name):
  if name.startswith(ACCOUNT_PREFIX):
    name = name[len(ACCOUNT_PREFIX):]
  return name

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")
