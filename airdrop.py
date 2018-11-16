# -*- coding: utf-8 -*-
import rpc
import simplejson as json
from utils import *
from credit_func import set_overdraft
import cache
from ops_func import *

THE_SENDER = u'discoin.bar'
wifs       = { 
  # u'discoin-gov'    : '5JxTiQ7hbAqVqvCsdZxzGBa6BsyypyFBTH9T499nyJMRz9PqZeW',
  u'discoin-gov'    : '5KU1QuhwwoJ5mJJuCgMXzXJx8FmhQvnPAfGgu7STJbPazUYxwHT',
  u'discoin.bar'    : '5JMUBHoECoScUVftGrGwiqecUpz7eYxSAVG1zxxngfQfHndfFX9'
}


def do_airdrop(airdrop_id, account_id, amount):
  asset, asset_core = rpc.db_get_assets([DISCOIN_ID, CORE_ASSET])
  to_id             = account_id 
  my_amount         = reverse_amount_value(amount, asset)
  my_amount_asset   = {
    'amount'   : my_amount,
    'asset_id' : DISCOIN_ID
  }
  # print(' -- my_amount_asset:', my_amount_asset)
  airdrop_id = str(airdrop_id or 1)
  memo = {
    'message' : '~ad:{0}'.format(airdrop_id).encode('hex')
  }
  # 7e61643a31
  # 7e61643a
  
  ops = transfer(
      cache.get_account_id(THE_SENDER),
      to_id,
      asset,
      amount,
      memo,
      None,
      DISCOIN_ID
  )
  print( ' == airdrop: ')
  print (ops)
  
  ret = set_fees_and_broadcast(ops, [wifs[THE_SENDER]], DISCOIN_ID)
  print ret

def do_process_airdrop():
  i=0
  for tmp in rpc.db_lookup_accounts(ACCOUNT_PREFIX , 100):
    if tmp[0].startswith(ACCOUNT_PREFIX + 'airdroptester'):
      i=i+1
      p = rpc.db_get_account_balances(tmp[1], [DISCOIN_ID])
      if try_int(p[0]['amount'])<=0:
        print(' -- #{0}'.format(i))
        print(json.dumps(tmp))
        print(json.dumps(p))
        do_airdrop('1', tmp[1], '101')

if __name__ == '__main__':
  do_process_airdrop()
  # do_airdrop('1', cache.get_account_id(u'discoin.airdroptester'), '101')
  # do_airdrop('1', cache.get_account_id(u'discoin.airdroptester2'), '1')
  