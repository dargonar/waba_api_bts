#from config import *
import decimal
import requests
import simplejson as json

class RpcError(Exception):
  def __init__(self, message, code):
    # Call the base class constructor with the parameters it needs
    super(RpcError, self).__init__(message)
    self.code = code

API_ID = {
  'db'      : 0,
  'network' : 2,
  'history' : 3,
}

def call_rpc(api, method, *params):
  url     = 'http://localhost:8090/rpc'
  headers = {'content-type': 'application/json'}
  auth    = ('user', 'pass')

  payload2 =  {
      "method": "call",
      "params": [API_ID[api], method] + [[p for p in params]],
      "jsonrpc": "2.0",
      "id": 10
  }

  r = requests.post(url, data=json.dumps(payload2), headers=headers, auth=auth, timeout=5)
  res = json.loads(r.text, parse_float=decimal.Decimal)
  if 'result' in res:
    return res['result']
  if 'code' in res['error']:
    raise RpcError(res['error']['message'], res['error']['code'])
  else:
    raise RpcError(res['error']['message'], 6969696969)

#--- new 2.x 
def db_get_assets(assets):
  return call_rpc('db', 'get_assets', assets)

def db_get_block_header(block_num):
  return call_rpc('db', 'get_block_header', block_num)

def db_get_block(block_num):
  return call_rpc('db', 'get_block', block_num)

def db_get_accounts(account_ids):
  return call_rpc('db', 'get_accounts', account_ids)

def db_get_account_by_name(name):
  return call_rpc('db', 'get_account_by_name', name)

def db_get_account_balances(account, assets=[]):
  return call_rpc('db', 'get_account_balances', account, assets)

def history_get_relative_account_history(account, stop=0, limit=100, start=0):
  return call_rpc('history', 'get_relative_account_history', account, stop, limit, start)

def db_get_transaction(block_num, trx_in_block):
  return call_rpc('db', 'get_transaction', block_num, trx_in_block)

def db_get_required_fees(ops, asset_id):
  if type(ops) != list: ops = [ops]
  return call_rpc('db', 'get_required_fees', ops, asset_id)

def db_get_global_properties():
  return call_rpc('db', 'get_global_properties')

def db_get_dynamic_global_properties():
  return call_rpc('db', 'get_dynamic_global_properties')
  
def db_get_chain_properties():
  return call_rpc('db', 'get_chain_properties')

def db_lookup_accounts(lower_bound_name, limit):
  return call_rpc('db', 'lookup_accounts', lower_bound_name, limit)  

def db_lookup_account_names(names):
  return call_rpc('db', 'lookup_account_names', names)  

def network_broadcast_transaction(tx):
  return call_rpc('network', 'broadcast_transaction', tx)

def participation_rate():
  return bin(int(db_get_dynamic_global_properties()['recent_slots_filled'])).count('1')*100.0/128.0
