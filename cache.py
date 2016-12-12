import unicodedata
import rpc
from memcache import Client

mc = Client(["127.0.0.1:11211"], debug=1)

def get_account(account_id):
  key = '?account_%s' % account_id
  account = mc.get(key)
  if not account:
    account = rpc.db_get_accounts([account_id])[0]
    mc.set(key, account)
  return account

def get_block_header(block_num):
  key = '?block_header%s' % block_num
  block_header = mc.get(key)
  if not block_header:
    block_header = rpc.db_get_block_header(block_num)
    mc.set(key, block_header)
  return block_header

# def get_account_id(mc, ws, account_name):
#   return ws.db_get_account_by_name(account_name)['id']

def get_account_id(account_name):
  key = '?account_id_%s' % unicodedata.normalize('NFKD', account_name).encode('ascii','ignore')
  account_id = mc.get(key)
  if not account_id:
    account_id = rpc.db_get_account_by_name(account_name)['id']
    mc.set(key, account_id)
  return account_id

def get_asset(asset_id):
  key = '?asset_id_%s' % asset_id
  asset = mc.get(key)
  if not asset:
    asset = rpc.db_get_assets([asset_id])[0]
    mc.set(key, asset)
  return asset
