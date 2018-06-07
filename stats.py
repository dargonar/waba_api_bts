from memcache import Client
import rpc
import utils  
import cache
import simplejson as json
import init_model
from models import *
# Base.metadata.create_all(get_engine())

def get_asset_supply(asset, mc):
  key = 'get_asset_supply_{0}'.format(asset)
  ret = mc.get(key) or None
  if ret:
    ret = json.loads(ret)
  if not ret:
    holders = rpc.db_get_asset_holders(asset, 0, 100)
    asset = cache.get_asset(utils.DISCOIN_ID)
#     print asset
    supply = utils.amount_value(sum(int(x['amount']) for x in holders), asset)
    ret = { 'supply' : supply, 'max_supply': utils.amount_value(asset['options']['max_supply'], asset), 'asset' : asset }
    mc.set(key, json.dumps(ret), 300)
  print('-- stats::get_asset_supply', json.dumps(ret))
  return ret

def get_asset_issuing_calendar(asset):
  # ToDo: en import guardar ops del tipo:
  #   15 - reserve (se saca de cicularion)
  #   14 + issue   
  # Traer de BBDDpass
  pass  

def get_asset_airdrop(asset, mc):
  # ToDo: setearop fake para los airdrop (69?) y en import guardar estas ops 
  # Traer de BBDD
  
  key = 'get_asset_airdrop_{0}'.format(asset)
  ret = mc.get(key) or None
  if ret:
    ret = json.loads(ret)
  if not ret:
    conf = {}
    with session_scope() as db:
      conf = db.query(NameValue).filter(NameValue.name=='configuration').first()
      if conf:
        db.expunge(conf)
      else:
        conf = init_model.get_default_configuration()
    ret = {
      'total_issued':    0,
      'by_referrals':       0,
      'by_reimbursment':    0,
      'by_transactions':    0
    }
    mc.set(key, json.dumps(ret), 300) 
  print('-- stats::get_asset_airdrop', json.dumps(ret))
  return ret
