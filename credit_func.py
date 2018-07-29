import rpc
import simplejson as json

from ops_func import *
from utils import ALL_TRACKED_ASSETS, DISCOIN_SYMBOL, DISCOIN_CREDIT_SYMBOL, DISCOIN_ACCESS_SYMBOL

wifs = {
  'discoin.admin'    : '5JQGCnJCDyraociQmhDRDxzNFCd8WdcJ4BAj8q1YDZtVpk5NDw9'
}

accounts = {}
assets   = {}
assets_by_id = {}

def account_id(name):
  return accounts[name]['account']['id']

def asset_id(name):
  return assets[name.upper()]['id']

def init(other_accounts):
  global accounts
  accounts = { a[0]:a[1] for a in rpc.db_get_full_accounts(list(set(list(wifs)+other_accounts)), False) }
  
  global assets
  global assets_by_id
#   assets = { a['symbol']:a for a in rpc.db_get_assets(['1.3.0','1.3.1236','1.3.1237','1.3.1319','1.3.1322','1.3.1320','1.3.1321']) }
  assets = { a['symbol']:a for a in rpc.db_get_assets(['1.3.0']+ALL_TRACKED_ASSETS) }
  
#   print '=================================================='
#   print 'credit_func::init'
#   print json.dumps(ALL_TRACKED_ASSETS)
#   print 'END =============================================='
  
  assets_by_id = { assets[k]['id']:assets[k] for k in assets }

def ops_for_remove(account_name, amount):
  res = override_transfer( 
    account_id('discoin.admin'),
    account_id(account_name),
    account_id('discoin.admin'),
    assets[DISCOIN_SYMBOL],
    reverse_amount_value(amount, assets[DISCOIN_SYMBOL])
  ) + asset_reserve(
    account_id('discoin.admin'), 
    assets[DISCOIN_SYMBOL], 
    reverse_amount_value(amount, assets[DISCOIN_SYMBOL])
  ) + override_transfer( 
    account_id('discoin.admin'),
    account_id(account_name),
    account_id('discoin.admin'),
    assets[DISCOIN_CREDIT_SYMBOL],
    amount
  ) + asset_reserve(
    account_id('discoin.admin'), 
    assets[DISCOIN_CREDIT_SYMBOL], 
    amount
  )

  return res

def ops_for_whitelist(account_name):
  res = account_whitelist(
    account_id('discoin.admin'),
    account_id(account_name),
    1 #insert into white list
  ) + account_whitelist(
    account_id('discoin.admin'),
    account_id(account_name),
    0 #remove from list (white or black)
  )
  return res

def ops_for_issue(account_name, amount):
  res = asset_issue( 
    account_id('discoin.admin'),
    account_id(account_name),
    assets[DISCOIN_SYMBOL],
#     reverse_amount_value(amount, assets[DISCOIN_SYMBOL])
    amount
  ) + asset_issue( 
    account_id('discoin.admin'),
    account_id(account_name),
    assets[DISCOIN_CREDIT_SYMBOL],
    amount
  ) 
  return res
#print json.dumps(res, indent=2)

# Set Overdrafts
def set_overdraft(accounts_to_issue):

  init(list(accounts_to_issue))
  
  print '=================================='
  print 'set_overdraft::accounts_to_issue'
  print json.dumps(accounts_to_issue)
  print accounts_to_issue
  print '=================================='
    
  ops = []
  for account, new_desc in accounts_to_issue.iteritems():

    print '=================================='
    print 'set_overdraft::account and new_OD'
    print account
    print account_id(account)
    print new_desc
    print '=================================='
    
    
    balances = rpc.db_get_account_balances(account_id(account), [assets[DISCOIN_SYMBOL]['id'], assets[DISCOIN_CREDIT_SYMBOL]['id']])
    print '=================================='
    print 'set_overdraft::check balances'
    print json.dumps(balances)
    print 'END =============================='
    acceptable_assets = [assets[DISCOIN_SYMBOL]['id'], assets[DISCOIN_CREDIT_SYMBOL]['id']]
    assert(balances[0]['asset_id'] in acceptable_assets), "Invalid 0 balance"
    assert(balances[1]['asset_id'] in acceptable_assets ), "Invalid 1 balance"
    
    par  = Decimal(amount_value( balances[0]['amount'], assets[DISCOIN_SYMBOL] ))
    desc = Decimal(amount_value( balances[1]['amount'], assets[DISCOIN_CREDIT_SYMBOL] ))
    
#     print ' -------- par#1:', par 
    if balances[0]['asset_id'] == assets[DISCOIN_CREDIT_SYMBOL]['id']:
      par  = Decimal(amount_value( balances[1]['amount'], assets[DISCOIN_SYMBOL] ))
#       print ' -------- par#2:', par 
      desc = Decimal(amount_value( balances[0]['amount'], assets[DISCOIN_CREDIT_SYMBOL] ))
    ops_w = ops_for_whitelist(account)

    if desc > new_desc:
      to_remove = desc - new_desc
      assert( par - to_remove >= 0 ), "account {0} => no hay par({1}) suficiente para sacar ({2})".format(account, par, to_remove)
      ops_w[1:1] = ops_for_remove(account, to_remove)
      ops.extend( ops_w )
    elif desc < new_desc:
      to_add = new_desc - desc
#       print ' -------- to_add:', to_add
      ops_w[1:1] = ops_for_issue(account, to_add)
      ops.extend( ops_w )

    # Lo limpiamos de la blacklist de propuesta (para q pueda recibir avals)  
#     ops += account_whitelist(
#       PROPUESTA_PAR_ID,
#       account_id(account),
#       0 #remove from black list
#     )

  assert( len(ops) > 0 ), "No hay operaciones parar realizar"
  #print json.dumps(ops, indent=2)
  #return
  
  print '======================================='
  print 'process::#1 about to set overdearft'
  print json.dumps (accounts_to_issue)
  print 'END ==================================='
  return set_fees_and_broadcast(ops, [wifs['discoin.admin']], CORE_ASSET)

#   return set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)
  #res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par'])
def ops_for_issue_simple(account_name, amount):
  res = asset_issue( 
    account_id('discoin.admin'),
    account_id(account_name),
    assets[DISCOIN_SYMBOL],
    amount
  ) 
  return res

def issue_reserve_fund(account_name, amount):
  init([])
  ops = ops_for_issue_simple(account_name, amount)
  return set_fees_and_broadcast(ops, [wifs['discoin.admin']], CORE_ASSET)

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

    # Lo limpiamos de la blacklist de propuesta (para q pueda recibir avals)  
    ops += account_whitelist(
      PROPUESTA_PAR_ID,
      account_id(account),
      0 #remove from black list
    )

  assert( len(ops) > 0 ), "No hay operaciones parar realizar"
  #print json.dumps(ops, indent=2)
  #return

  return set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)
  #res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par'])

def multisig_delete_proposal(proposal_id):
  init([])
  ops = proposal_delete(account_id('gobierno-par'), proposal_id)
  res = proposal_create(account_id('propuesta-par'), ops, wifs['propuesta-par']) #)

def WARNING_multisig_bring_them_all_proposal(account):
  init([])
  
  ops = []
  for u in rpc.db_get_asset_holders(assets['MONEDAPAR']['id']):
    #if u['name'] == 'gobierno-par': continue
    if u['name'] != account: continue

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
    #if u['name'] == 'gobierno-par': continue
    if u['name'] != account: continue

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
  #set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)
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

def multisig_change_keys(account, owner, active, memo_key):
  init([account])

  active_auth = {
    'weight_threshold' : 1,
    'account_auths'    : [],
    'key_auths'        : [[active,1]], 
    'address_auths'    : []
  }
  
  owner_auth = {
    'weight_threshold' : 1,
    'account_auths'    : [[account_id('discoin.admin'),1]],
    'key_auths'        : [[owner,1]], 
    'address_auths'    : []
  }
  
  ops = account_update(
    account_id(account), 
    owner_auth, 
    active_auth, 
    {'memo_key':memo_key},
    [wifs['discoin.admin']]
  )
  
#   ,
#     assets['DISCOIN']['id']

  #[wifs['marcio'], wifs['beto']]
  #set_fees_and_broadcast(ops, None, CORE_ASSET)
  
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

def WARNING_clean_account(orig):
  
  balances = rpc.db_get_account_balances(account_id(orig))
  print json.dumps(balances, indent=2)

  ops = []

  # print json.dumps(assets_by_id, indent=2)

  for b in balances:
    if b['amount'] == 0 : continue
    #print b['asset_id'], b['asset_id'] != '1.3.0'
    if b['asset_id'] != '1.3.0':

      ops += transfer(
        account_id(orig),
        assets_by_id[b['asset_id']]['issuer'],
        assets_by_id[b['asset_id']],
        amount_value(b['amount'], assets_by_id[b['asset_id']])
      )

  print len(ops)

  if len(ops) == 0:
    print "nada para limpiar en ", orig
    return

  ops = transfer(
    account_id('propuesta-par'),
    account_id(orig),
    assets['BTS'],
    amount_value(130625*len(ops), assets['BTS'])
  ) + account_whitelist(
    account_id('gobierno-par'),
    account_id(orig),
    1 #insert into white list
  ) + account_whitelist(
    account_id('propuesta-par'),
    account_id(orig),
    0 #remove from lists
  ) + ops

  tx = build_tx_and_broadcast(
    ops,
    [wifs['moneda-par.prueba'],wifs['propuesta-par'],wifs['marcio'],wifs['beto']]
  )

  print json.dumps(tx, indent=2)  


if __name__ == '__main__':
  #pass
  #init([])
  #WARNING_clean_account("moneda-par.prueba")

  #WARNING_multisig_bring_them_all_proposal("moneda-par.prueba")

  # asset1, asset2 = rpc.db_get_assets(['1.3.1320', '1.3.1322'])
  
  # print "***********************************************************"
  # print "***********************************************************"
  # print "***********************************************************"

  # print asset1
  
  # memo  = {
  #   'message' : '~et:prueba'.encode('hex')
  # }

  # set_fees_and_broadcast(
  #   transfer(
  #     account_id('moneda-par.matias'),
  #     account_id('propuesta-par'),
  #     asset1,
  #     3,
  #     memo,
  #   ) + transfer(
  #     account_id('moneda-par.matias'),
  #     account_id('propuesta-par'),
  #     asset2,
  #     2,
  #     memo,
  #   ),
  #   wifs['moneda-par.matias'],
  #   asset_id('monedapar')
  # )


  # ops = []
  # ops.extend( 
  #   account_whitelist(
  #     account_id('propuesta-par'),
  #     account_id('moneda-par.prueba'),
  #     0 #delist
  #   )
  # )
  # print json.dumps(ops, indent=2)
  # set_fees_and_broadcast(ops, [wifs['marcio'], wifs['beto']], CORE_ASSET)

  # init([])
  # new_options = {
  #   "max_supply": "100000000",
  #   "market_fee_percent": 0,
  #   "max_market_fee": 0,
  #   "issuer_permissions": 79,
  #   "flags": 78,
  #   "core_exchange_rate": {
  #     "base": {
  #       "amount": 100000,
  #       "asset_id": "1.3.0"
  #     },
  #     "quote": {
  #       "amount": 1,
  #       "asset_id": assets['MONEDAPAR.AC']['id']
  #     }
  #   },
  #   "blacklist_authorities" : [ account_id('propuesta-par') ],
  #   "description" : json.dumps({"main":"Aval de credito PAR x 100000","short_name":"","market":""})
  # }
  
  # asset_update(
  #   account_id('propuesta-par'), 
  #   assets['MONEDAPAR.AC']['id'],
  #   new_options, 
  #   wif=[wifs['marcio'], wifs['beto']]
  # )


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

  #accounts_to_issue = {
  #  "moneda-par.hectorh"    : 1000
  #}

  #multisig_set_overdraft(accounts_to_issue)

  #print withdraw_permission_create(
  #  account_id('matias'), 
  #  account_id('beto'), 
  #  amount_of(assets['MONEDAPAR'], 100), 
  #  86400,
  #  30,
  #  format_date(calc_expiration(datetime.utcnow(), 120)),
  #  wifs['matias']
  #)

  #init(["moneda-par.edith", "moneda-par.belosoler"])

  #x = multisig_change_keys(
  #  "moneda-par.edithe",
  #  "BTS8QGHdWueerJE8SMqwM65iyWqL6cxXPisg31GdD7eqGStZEEzbL",
  #  "BTS6BgD83U7sX82M2vybwJEYwrMQnGiHDu23JNXSfaPxaTRgAXgT8",
  #  "BTS6ajNfJEZwwm3g83zYy86kGGwcaBhnBdsHMTcDHHZ7AAKyjjLTH"
  #)

#   y = multisig_change_keys(
#     "moneda-par.andrea",
#     "BTS8YFwSiJvn1r4oenmft9Hkvy9Rp8s1mzYczXVKtz3McGAmJa6Bm",
#     "BTS62V2rhWwJefWzri5zs9viBFNScnzAwdLgQAdtvbCjLsyEEoN7o",
#     "BTS8SwCfDUC7fQtgKzyQRC5AT7CKB7RxTkhSFRzjdCnTKeetF3PYr"
#   )
  y = multisig_change_keys(
    "discoin.biz4",
    "BTS5jeqUg2MZ3beav5u7mb56ZMH65LKiAoe7QvJWmHxkjwdBVj3L2",
    "BTS5jeqUg2MZ3beav5u7mb56ZMH65LKiAoe7QvJWmHxkjwdBVj3L2",
    "BTS5jeqUg2MZ3beav5u7mb56ZMH65LKiAoe7QvJWmHxkjwdBVj3L2"
  )

  #accounts_to_issue = {
  #  "moneda-par.elmercado"    : 30000
  #}
  #multisig_set_overdraft(accounts_to_issue)
