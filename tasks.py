from models import *
from utils import *

import rpc

def update_holders(db):
  holders = rpc.db_get_asset_holders(ASSET_ID)
  for h in holders:
    acc, is_new = get_or_create(db, AccountBalance, account_id=h['account_id'], asset_id=ASSET_ID)
    acc.account_name = h['name']
    acc.amount       = h['amount']
    db.add(acc)

def money_per_day():
  pass
  