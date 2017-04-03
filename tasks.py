from models import *
from utils import *

import rpc

def update_holders(db, asset_id):
  holders = rpc.db_get_asset_holders(asset_id)
  for h in holders:
    acc, is_new = get_or_create(db, AccountBalance, account_id=h['account_id'], asset_id=asset_id)
    acc.account_name = h['name']
    acc.amount       = h['amount']
    db.add(acc)

def money_per_day():
  pass
  
