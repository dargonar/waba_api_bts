import rpc
import simplejson as json

from ops_func import *

wifs = {
 'matias'            : '5Jg4pQNnJdMboeRaFa1dQznDt2fc4GunjSLPtJZ828grKv1SxTm',
 'beto'              : '5JiF8n5nxoJX6qQ45VVtURnTBZvbPBMTb756WptAkNZGMfpgw3e',
 'marcio'            : '5K41mU4XhmbJ2ZX3fSqhoFi1iVKYcwvM3e84tKuLbKGPm5SxWPd', 
 'propuesta-par'     : '5K5p1J9yXWpY9qvpD2CTv5VLqmda4QxqayQT2w3Q2vRW9xfVhwd',
 'petoelpatoputo'    : '5HuSJENqeLwKEdJDFRahhKvdniqt4V2RZSnMSd9MrU82EhSGuhW',
 'gobierno-par'      : '',
 'moneda-par.prueba' : '5Hqk35nSEHYFRXsrZgpZ5yuHv6Nged7hmWCrrbYazeJwDKSYWFZ',
 'moneda-par.matias' : '5KaMXhrGoHcNJuoZ25ZieM4BLhBR7xwXu64UncX3FaUTJ2Kx9fG'
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
  assets = { a['symbol']:a for a in rpc.db_get_assets(['1.3.0','1.3.1236','1.3.1237','1.3.1319','1.3.1322','1.3.1320','1.3.1321']) }
  assets_by_id = { assets[k]['id']:assets[k] for k in assets }

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
    'account_auths'    : [[account_id('gobierno-par'),1]],
    'key_auths'        : [[owner,1]], 
    'address_auths'    : []
  }
  
  ops = account_update(
    account_id(account), 
    owner_auth, 
    active_auth, 
    {'memo_key':memo_key},
    [wifs['marcio'], wifs['beto']],
    assets['MONEDAPAR']['id']
  )

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

  #y = multisig_change_keys(
  #  "moneda-par.andrea",
  #  "BTS8YFwSiJvn1r4oenmft9Hkvy9Rp8s1mzYczXVKtz3McGAmJa6Bm",
  #  "BTS62V2rhWwJefWzri5zs9viBFNScnzAwdLgQAdtvbCjLsyEEoN7o",
  #  "BTS8SwCfDUC7fQtgKzyQRC5AT7CKB7RxTkhSFRzjdCnTKeetF3PYr"
  #)

#  y = multisig_change_keys(
#	"moneda-par.mariocaf",
#	"BTS7UM4yTeuwx7yWcJC3uXNDUgLfktB2gaa12pzhQHa2ekr8qdUSH",
#	"BTS8ekzCRDxj3kMa8ZpxD6xYX3k6jyJNn9NRAUMrHeorvJ5B6PVNs",
#	"BTS5hKYaSA1QNWNGQ1cnkV1atK53nKVxaucuzfYQB24D4tWrDagMJ"
 # )


  #y = multisig_change_keys(
#	"moneda-par.impa",
#	"BTS6VxVk7KjFgrgknYxDGKFZSEb8MEpC9oZjRcgazYpEQkPATeE9t",
#	"BTS5qEg4uzvTEHTBv667SGCG5zAewcyJLJu1NeMz2eN7ukhm1XvzU",
#	"BTS8Bo36t1gSnQgbYe1dszHLvvkeNRuTG6Sc2KdcagkKZdMDYfobW"
 # )

 # y = multisig_change_keys(
#	"moneda-par.dani",
#	"BTS8LSi1LrEsqFnYNU6nvEacEg4xvH5mnCfnhwNkCnWi7U8ekFeNb",
#	"BTS65ono92Uvob3FMbkYcutMzfoWraEoTCaTYx4rbEQALDrtgMSFY",
#	"BTS5JqfqGFwLZobdEt4dp83mJWvsdoJ5a6immWoVC2g8sQgZwusgm"
#  )
  
  
  #y = multisig_change_keys(
#	"moneda-par.donadominga",
#	"BTS7HiB8L5UwtRP7EkQ2oLDcf5kayzvoZo6suntCneB6aiJjwZ8Kf",
#	"BTS6GNwaR4i2cjAH63c4Y4E3vkWpfZemHEYJ4yZh6hPuAprY6SwjT",
#	"BTS6dGhoDB5TjZGjhNpK29N9hRxyUcVShS9TxWj9pUdApzAep9JWn"
 # )

#  y = multisig_change_keys(
#       "moneda-par.alejandraocampp",
#       "BTS6ug3ek7BvWuHWPBz2DYTzBy7briH1VNrmSWmTBq8yKr3GhRLGy",
#       "BTS6UwnYhD5vVhCzmTGyzrPD4B3A5T2hEdRjPQDH7ZM6NwbEvzHSx",
#       "BTS87iBF12mbwjMYzCnWc29oUmUPuKTePyGoY128C2aDNdL8K8wfz"
#  )   
#  y = multisig_change_keys(
#       "moneda-par.pamelaps",
#       "BTS5XobFBLoknZAgYC5VBoGLSUwacMrzvw1cP72rLB2zcVNL8mKdr",
#       "BTS5TSk4vxw1Pi4pinvyqB6KsF2fUm5nzrKsnQjwcRav4VrwECc4U",
#       "BTS7qbJztjuXBoCcoZbDXUjWKtEe7Mikyp2XLBSe1qtXKimJfKdqm"
#  ) 
  #y = multisig_change_keys(
#	"moneda-par.nodomardelplata",
#	"BTS6PFdocwBkMf9Hj9wiMFMqQQEEUxPMVkVrcoQQmYapz6wPwqTYQ",
#	"BTS8K3CUmAQ5qV7nEyJ8KTSUhtVBaK9gxFCqkcYqWMtBcT9iAAzZd",
#	"BTS8NAUTgPWFHfgVjqYzBpUoYG9TCbY92uGJpur3PuW1LLPQNLhWC"
 # )
 # y = multisig_change_keys(
#	"moneda-par.asdrubal",
#	"BTS8NcJ4yzVHE18fU1XYJjf1B5dhX9QwFcAc1NnNfmt9AcZr6s5ps",
#	"BTS5WTigaxjdDck71pbiMJGKJ5oAdWhhacz7mJier2biQ8qyteQMh",
#	"BTS7azfBJgrL9Gdi4PVejtkajTZxr3k3uPP2F4mph4vp2QucVXfzU"
 # )
 # y = multisig_change_keys(
#	"moneda-par.irma",
#	"BTS5ZLdfzTKsDQTbCX3jcAs7UtKj7FJECKpLM8ZWia32yBPV6inCV",
#	"BTS6QF4FSc43YJqGrXN4LYshuX6Szoo8sLoaJLzVFXxyPdnewDwk8",
#	"BTS4tyB58AQiGFm9em5tRE4L6zMXfDVKd99hwPtBo965BE6j1WkGf"
 # )
  #y = multisig_change_keys(
#		"moneda-par.nodobuenosaires",
#		"BTS8ci4v7NrQXSA9vwdf9Z5GC4rKb3CgEtdEJgXKWK154SgkpATPQ",
#		"BTS7uC6dVGc1cL41PCXbWyYTTZRD16Mt4hRnK3eTkoQYMzeftbPbJ",
#		"BTS8D63rHXcHTNvhSdw6xrKVn9SjHXYXkVHrupp9Nh9EkSVhwPBsL"
#	) 

  #y = multisig_change_keys(
#		"moneda-par.asdrubal",
#		"BTS6dhhExmeiqVbMFLHydi9UFnv9zgtnPPHeoFYbjmNM83SQ3oMKd",
#		"BTS77skH8AcADiSxvC8kpQsM16AJjRxFZVvbsB2qUNc31rHKhisrg",
#		"BTS73ABL35CizLekGi3QHBmL7ewQJKjYcVWC6ssbp6zLFLohrADBq"
#	)
 # y = multisig_change_keys(
#		"moneda-par.nodomardelplata",
#		"BTS6Hfs5iEbpvucBez8auNEuswVQJGcGYWDAcpsiAmWEEpfRi4rhQ",
#		"BTS7xAikkn4vmwmBP9XYUcMGxA94UEYLN8uB8DYEfadyhcPcJ7a5b",
#		"BTS7VMS55RG9awaCweEG6DSSYvQDc5GG7CbSYUesb5FQPdbWJr3FK"
#	)
  #y = multisig_change_keys(
#		"moneda-par.nodobuenosaires",
#		"BTS65udWi51xx1EHJp1XyH1DL29tMgenvNQJ4nfsLdcEdTZFeyefq",
#		"BTS77wtGTGi31WUp2z98Mi96eQiP8GZuBQ6Hoc4VmcUHAC8so2aae",
#		"BTS59vSVHqniFr2HyrX4RXAa8bFAKogEpVG5HrhKzgPvZ2qf69S85"
#	)
  #y = multisig_change_keys(
#		"moneda-par.leonelmachado",
#		"BTS5u4wrkxKiuedTSXBRQUi83i5nLNydCgnRdN5Tj7KcdoYRrL9z8",
#		"BTS8JibLWyVkVnTgxhwGuGLQC2D9xZeLybnSRKS6K72J7tWZ46dSX",
#		"BTS6fUJBw8EeudoskZTo1NR2avZGGpsUjvRED3Nv4XJPJY5rsNAbo"
#	)

 # y = multisig_change_keys(
#		"moneda-par.lunajorg40",
#		"BTS6QGKQPv4Ltha5dG6EywUbdJSFenw78BVL8KVQtLZE5zobYbZ9S",
#		"BTS7vScGXUPCT2EpdjnuU2J5rscdsW5DMpTkbnn9wbXjrYxNythNc",
#		"BTS5FfASLnWUXuRqiw5dhdU6L4e6qqVeTva631fpZqepKa81T8YGG"
#	)

#  y = multisig_change_keys(
#		"moneda-par.leomachado",
#		"BTS73UXsAiwghrtQ6ew9yNceZrNGQG3oJK9EwqmwfbbDDKx65rUfE",
#		"BTS5xCXTfJ6Yfhqjo3jALq27zDcedRGMv4kfxRUVKGMHzQ6ifsFj5",
#		"BTS6VxZ6qredcV1Zv9TYtzwpxUXWesVad95RpnNv48GotgysVDpb5"
#	)
#  y = multisig_change_keys(
#	"moneda-par.corinam",
#	"BTS58mkdR8za3SGr3yias9noHqkHatWyirDojghYdvxFD9cUe1nVh",
#	"BTS53PL5UCAEDSZKqWsEZwFgJqxLdZ8GxUvB9cmFAsu4QtTHkxNsv",
#	"BTS8RdBmeifNkkjrahPizj8rBeWb9PwHh22ruLMPG1TktoG8yVpHd"
#  )

#  y = multisig_change_keys(
#	"moneda-par.creacionesmarcela",
#	"BTS8k7XecsxMX4wQ2FGMKNrNnDsPr8WgreTtZKno79NNda1P6k5Mi",
#	"BTS5jpjws4fQnspAKHMELRyQ2Mn7UChiyAbp6j24whyef5pZ35ioK",
#	"BTS8gSPrkYNTDnJPWG9336UX6Q5rCyYH9ma5fHa8ks4EpA63JMKEf"
#  )

 # y = multisig_change_keys(
#		"moneda-par.nodogualeguaychu",
#		"BTS6AwtjAqrSoPrmUka43Fa8uaJZ5eaAHy1zDvun6xkJUaXg6UA2r",
#		"BTS6Hmtw1BG4XKmcp6wHDBo7oS7KjU2S5iJyeUhePrvSWXd72DKsk",
#		"BTS8CLitjv9CcZGbpYisfvVMnG8JwiMpAeAsuaGt1EadxkGRBXE4H"
#	)

#  y = multisig_change_keys(
#		"moneda-par.nicoechaniz",
#		"BTS8jKtEyY55VPwTq8Q3LY8htbZXpXzhovdR3r2dZHX9Ph2MxfcxE",
#		"BTS8QEBB7JKUSXSDJ68Swp7kdzNTHyHJAYM8P8KgQ2aQ3xW3W56Dq",
#		"BTS6cBWCA5M6eQovoYuFJ3L6o5yjWA9z6iWPKebqZBeuYNWiZmxKn"
#	)

#  y = multisig_change_keys(
#		"moneda-par.nodomoreno",
#		"BTS8SokH4fJNLmfXKJJgz73EaRbKXHMTHRDZrutgnDEygxQN9iQN4",
#		"BTS5cDR38wPGWBbYHxXKkPEKaiyKoZeYhTE24aknTdHASfUjgBcXb",
#		"BTS855yELosJLP1mgEd38WTunPLHH7ZcBSVBdHKxyu9ZB3mxQ261v"
#	)

#  y = multisig_change_keys(
#		"moneda-par.alesole",
#		"BTS6CF25A7emrqx1CizdeviwqV299MyDc2dWM8b2vSHJuTB1jvypd",
#		"BTS8YsUEzgTquSsWc6t5csCCLqA1GKDfUo4R8M46EovDzHkLhxTFm",
#		"BTS4ui6WvDZTPvUUJjGhkRAbQfwQ8k1BGn7FCCPXacxzZxRpjV6WT"
#	)

#  y = multisig_change_keys(
#		"moneda-par.nodoescobar2",
#		"BTS4tZFyBhqDYcZ3rP3x38XxasDXbM1SYTGbKxVmkfzUYSWzagPeM",
#		"BTS8RUqw3iXTGB22C9fwrecr8yjbKhYWpszcjpvhqmpUGrLP6iebu",
#		"BTS5Wt2LvHHWvFTVUhzmrUcMpZQ8JKi4f3UK7zzG9rGkYR7jFaS2X"
#	)

#  y = multisig_change_keys(
#		"moneda-par.nodoescobar3",
#		"BTS6Jn1CNZbADXMxCqwgpy47WL4VdG2P8MhjbZmnbetaNd3KWVqwU",
#		"BTS8ZGBygKDDj5mxHXPiBvo8N88J6GBipGGrQRaqPkQmirss2hoso",
#		"BTS6eCuJaddDZvvAHCGMu7Y1Dswp5x12LqbZyfBDAeBgQLtR71NMn"
#	)

#  y = multisig_change_keys(
#		"moneda-par.establecimientooktubre",
#		"BTS6JU8NBBFFdHuWjGXddopHArqvjVekkRLRBULQ6c88U88VVJZUG",
#		"BTS5EztZ3CQGP9VydB7GoFL8MJpVYxfgVCRv1GDFnzivzTi2wcG2k",
#		"BTS7Sy1GchqaGGmipK4uodoBW6eepKcnr8z1BjhqceoVfxp8RPhJP"
#	)

#  y = multisig_change_keys(
#		"moneda-par.belen.escanes",
#		"BTS8TCS3kzcQaj3qp6pt5jDvkT1URtEGhjGmPkyKF1CQnvN4wWMwR",
#		"BTS5QgXovuhsakU2JqtEM7MwJgW6SnVLsmNJKKMgQmzMDAyfrY93g",
#		"BTS6681GcMJWyCwdMbekSk9cZJfPmtLQi6bbKc9bjqzeAGHjiGC87"
#	)
# y = multisig_change_keys(
#		"moneda-par.nodoboedo",
#		"BTS85XPKPngfaF5mgubwqwCKUDStMY9UCyp2D7WQrCd7oCiA9vHBK",
#		"BTS8CLaSvwGEdJU4Y6ZYUMWcVzwrz6Udn2Kckn11j3SL6vXkXjSYe",
#		"BTS6QdaagW3JyDeM8idYhQnxNPErHTVXxbKd68QFUxtYQ3Xo9PF8n"
#	)

#  y = multisig_change_keys(
#	"moneda-par.nancy869",
#	"BTS7QX54GAeRjqyruX4GDStFPuLXxCF7iXew8bTSupUH

#  y = multisig_change_keys(
#	"moneda-par.susana",
#	"BTS7jjphGRCNXQnrJtzpFBYqByQDGK2ctS3jnDn192CgDUcRPwR9B",
#	"BTS6z8UXDFKjvkViiyUCF3YpDRV9aLRdjsakipBRTGfjzPHywPzXw",
#	"BTS5MLwd5gxPqMeUom1xRCNFHzfG5mdJpva9KL9J76KphBuHiJExs"
#)
#  y = multisig_change_keys(
#	"moneda-par.veroro",
#	"BTS7iqnX13x88vmqFojBFc2pWqc3kDsjWf1E9jPQpJNZNFYZcpMMt",
#	"BTS5a3sNwFG9rotBj5b61SyXUPFCheNSH4NwKR5rqx1Q6sYHrDnFD",
#	"BTS68Jut4X282avzMzAAa5uRiyR9Jx3LNXGhx8KPtMhBctw3TZSUh"
#)

  y = multisig_change_keys(
	"moneda-par.edith",
	"BTS6JV3wDEbudhYEorYmFc7bSJhMhceCpvbWzxYP6yXghEAfvtqDV",
	"BTS8WRhgoSHP3Pir5A2fwDjM7fjouiB6rv6Achpd4KJQSdUxi7jUw",
	"BTS7onyfwsDw4cCZ6Tz8wR8iEaDLsqVD8h47SqeNRPA7c25Q2Qnw6"
)
  
  y = multisig_change_keys(
	"moneda-par.nantili",
	"BTS8BKFf6FXVKYg2gkV1NzzkcLRSYdjhYarWvF76JMfNCR1YbqDJW",
	"BTS7hPgdA6cyuGAGtM9daif6Lm5syDoWkTyGa7FA47fefqbhHrXxr",
	"BTS55P2QtfvQYU4uhuzULZQYUH7SLJoni2qq3e9tf6S9eKPmQ1GTa"
)

  y = multisig_change_keys(
	"moneda-par.delfosmet",
	"BTS68ngDnmQj1aQZ4pcCBZaxG7UNEmc3Si9tSmFYXWtJNFY7m2ep7",
	"BTS6VbTg6Cn9VX2bTuR43XwVK2o6yW5uhsK3gVivBuqMMiqA9QeMg",
	"BTS5LSLx7otLtNLeYu3TgDnCW8ybo4qWMmhb4YQb9s1yaSR7wEekc"
)
#accounts_to_issue = {
  ##  "moneda-par.elmercado"    : 30000
  #}
  #multisig_set_overdraft(accounts_to_issue)
