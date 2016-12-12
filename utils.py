TEST_PESOCIAL = 'test-pesocial.' 
ASSET_ID      = '1.3.1004'
DB_URL        = 'mysql+pymysql://root:248@127.0.0.1/par'

from decimal import Decimal

def amount_value(amount, asset):
  d = Decimal(amount)/Decimal(10**asset['precision'])
  return str(d)

def real_name(name):
  if name.startswith(TEST_PESOCIAL):
    name = name[len(TEST_PESOCIAL):]
  return name
