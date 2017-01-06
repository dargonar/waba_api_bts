import rpc
import simplejson as json

from ops_func import *

wifs = {
 'matias'         : '5Jg4pQNnJdMboeRaFa1dQznDt2fc4GunjSLPtJZ828grKv1SxTm',
 'beto'           : '5JiF8n5nxoJX6qQ45VVtURnTBZvbPBMTb756WptAkNZGMfpgw3e',
 'marcio'         : '5K41mU4XhmbJ2ZX3fSqhoFi1iVKYcwvM3e84tKuLbKGPm5SxWPd', 
 'propuesta-par'  : '5K5p1J9yXWpY9qvpD2CTv5VLqmda4QxqayQT2w3Q2vRW9xfVhwd',
 'petoelpatoputo' : '5HuSJENqeLwKEdJDFRahhKvdniqt4V2RZSnMSd9MrU82EhSGuhW',
 'gobierno-par'   : '',
}

accounts = {}
assets   = {}

def account_id(name):
  return accounts[name]['account']['id']

def init(other_accounts):
  global accounts
  accounts = { a[0]:a[1] for a in rpc.db_get_full_accounts(list(set(list(wifs)+other_accounts)), False) }
  
  global assets
  assets = { a['symbol']:a for a in rpc.db_get_assets(['1.3.1236','1.3.1237']) }

def ops_for_remove(account_name, amount):
  res = override_transfer( 
    account_id('gobierno-par'),
    account_id(account_name),
    account_id('gobierno-par'),
    assets['MONEDAPAR'],
    amount
  ) + asset_reserve(
    account_id('gobierno-par'), 
    assets['MONEDAPAR'], 
    amount
  ) + override_transfer( 
    account_id('gobierno-par'),
    account_id(account_name),
    account_id('gobierno-par'),
    assets['DESCUBIERTOPAR'],
    amount
  ) + asset_reserve(
    account_id('gobierno-par'), 
    assets['DESCUBIERTOPAR'], 
    amount
  )

  return res

def ops_for_whitelist(account_name):
  res = account_whitelist(
    account_id('gobierno-par'),
    account_id(account_name),
    1 #insert into white list
  ) + account_whitelist(
    account_id('gobierno-par'),
    account_id(account_name),
    0 #remove from list (white or black)
  )
  return res

def ops_for_issue(account_name, amount):
  res = asset_issue( 
    account_id('gobierno-par'),
    account_id(account_name),
    assets['MONEDAPAR'],
    amount
  ) + asset_issue( 
    account_id('gobierno-par'),
    account_id(account_name),
    assets['DESCUBIERTOPAR'],
    amount
  ) 
  return res
#print json.dumps(res, indent=2)

# Multisig proposals
def multisig_set_overdraft(accounts_to_issue):

  init(list(accounts_to_issue))

  ops = []
  for account, new_desc in accounts_to_issue.iteritems():

    balances = rpc.db_get_account_balances(account_id(account), [assets['MONEDAPAR']['id'], assets['DESCUBIERTOPAR']['id']])
    assert(balances[0]['asset_id'] == assets['MONEDAPAR']['id']), "Invalid 0 balance"
    assert(balances[1]['asset_id'] == assets['DESCUBIERTOPAR']['id']), "Invalid 1 balance"
    
    par  = Decimal(amount_value( balances[0]['amount'], assets['MONEDAPAR'] ))
    desc = Decimal(amount_value( balances[1]['amount'], assets['DESCUBIERTOPAR'] ))

    ops_w = ops_for_whitelist(account)

    if desc > new_desc:
      to_remove = desc - new_desc
      assert( par - to_remove >= 0 ), "account {0} => no hay par({1}) suficiente para sacar ({2})".format(account, par, to_remove)
      ops_w[1:1] = ops_for_remove(account, to_remove)
      ops.extend( ops_w )
    elif desc < new_desc:
      to_add = new_desc - desc
      ops_w[1:1] = ops_for_issue(account, to_add)
      ops.extend( ops_w )
  
  assert( len(ops) > 0 ), "No hay operaciones parar realizar"
  #print json.dumps(ops, indent=2)
  #return
  set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)
  #res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par'])

def multisig_delete_proposal(proposal_id):
  init([])
  ops = proposal_delete(account_id('gobierno-par'), proposal_id)
  res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par']) #)

def WARNING_multisig_bring_them_all_proposal():
  init([])
  
  ops = []
  for u in rpc.db_get_asset_holders(assets['MONEDAPAR']['id']):
    if u['name'] == 'gobierno-par': continue
    if u['amount'] == 0: continue
    ops.extend( 
      override_transfer( 
        account_id('gobierno-par'), 
        u['account_id'], 
        account_id('gobierno-par'),
        assets['MONEDAPAR'], 
        Decimal(amount_value(u['amount'], assets['MONEDAPAR']))
      )
    )

  for u in rpc.db_get_asset_holders(assets['DESCUBIERTOPAR']['id']):
    if u['name'] == 'gobierno-par': continue
    if u['amount'] == 0: continue
    ops.extend( 
      account_whitelist(
        account_id('gobierno-par'),
        u['account_id'],
        1 #insert into white list
      ) + override_transfer( 
        account_id('gobierno-par'), 
        u['account_id'], 
        account_id('gobierno-par'),
        assets['DESCUBIERTOPAR'], 
        Decimal(amount_value(u['amount'], assets['DESCUBIERTOPAR']))
      ) + account_whitelist(
        account_id('gobierno-par'),
        u['account_id'],
        1 #insert into white list
      )
    )
  print json.dumps(ops, indent=2)
  set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)
  #res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par'])
  #print json.dumps(ops, indent=2)

def multisig_change_government_active(active):
  init([])
  ops = account_update(account_id('gobierno-par'), None, active)
  res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par'])

def multisig_reserve_asset(assets_to_reserve):
  init([])

  balances = rpc.db_get_account_balances(account_id('gobierno-par'), [assets[a]['id'] for a in assets_to_reserve])
  
  ops = []
  for j in xrange(len(assets_to_reserve)):
    assert(balances[j]['asset_id'] == assets[assets_to_reserve[j]]['id']), "Invalid 0 balance"
    if balances[j]['amount'] == 0: continue
    amount = amount_value(balances[j]['amount'], assets[assets_to_reserve[j]])
    ops.extend(
      asset_reserve(account_id('gobierno-par'), assets[assets_to_reserve[j]], amount)
    )
  
  set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)
  #res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par'])

def multisig_claim_fees(assets_to_claim):
  init([])
  
  oinfo = rpc.db_get_objects([ 
    ainfo['dynamic_asset_data_id'] for ainfo in rpc.db_get_assets([assets[asset]['id'] for asset in assets_to_claim])
  ])
  
  ops = []
  for j in xrange(len(assets_to_claim)):
    
    asset = assets[assets_to_claim[j]]
    
    assert(oinfo[j]['id'][1:] == asset['id'][1:]), "Invalid claim"
    if oinfo[j]['accumulated_fees'] == 0: continue
      
    amount = amount_value(oinfo[j]['accumulated_fees'], asset)
    ops.extend(
      asset_claim_fees(account_id('gobierno-par'), asset, amount)
    )
  
  set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)
  #res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par'])

if __name__ == '__main__':
  #pass
#   init([])
#   new_options = {
#     "max_supply": "10000000000",
#     "market_fee_percent": 0,
#     "max_market_fee": 0,
#     "issuer_permissions": 79,
#     "flags": 14,
#     "core_exchange_rate": {
#       "base": {
#         "amount": 100000,
#         "asset_id": "1.3.0"
#       },
#       "quote": {
#         "amount": 100,
#         "asset_id": "1.3.1237"
#       }
#     },
#     "whitelist_authorities" : [ account_id('gobierno-par') ]
#   }
  
#   asset_update(
#     account_id('gobierno-par'), 
#     assets['DESCUBIERTOPAR']['id'], 
#     new_options, 
#     wif=[wifs['marcio'], wifs['beto']]
#   )
  
  
  #multisig_claim_fees(["MONEDAPAR","DESCUBIERTOPAR"])
  #multisig_reserve_asset(["MONEDAPAR","DESCUBIERTOPAR"])
  #WARNING_multisig_bring_them_all_proposal()
  accounts_to_issue = {
    "moneda-par.matias" : 100, 
#     "testtest.pepita3" : 500, 
#     "testtest.pepita4" : 750,
#     "matu"             : 2500
  }
  multisig_set_overdraft(accounts_to_issue)
  