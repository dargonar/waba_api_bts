# -*- coding: utf-8 -*-
import rpc
import simplejson as json
from utils import *
from credit_func import set_overdraft
import cache
from ops_func import *

THE_SENDER = u'discoin.discoin'
wifs       = { 
  #u'discoin-gov'    : '5JxTiQ7hbAqVqvCsdZxzGBa6BsyypyFBTH9T499nyJMRz9PqZeW',
  #u'discoin-gov'    : '5KU1QuhwwoJ5mJJuCgMXzXJx8FmhQvnPAfGgu7STJbPazUYxwHT',
  #u'discoin.bar'    : '5JMUBHoECoScUVftGrGwiqecUpz7eYxSAVG1zxxngfQfHndfFX9',
  'discoin.discoin'  : '5JtuS6C9urZrmij9G3FyWWkzgyfQRC3GEdbBGGFZtesjYZsAGN5'
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
  #print( ' == airdrop: ')
  #print (ops)
  
  ret = set_fees_and_broadcast(ops, [wifs[THE_SENDER]], DISCOIN_ID)
  #print ret

def do_process_airdrop():
  i=0
  _sent = ['discoin.erminia', 'discoin.ezeagesilao', 'discoin.eric.williams91', 'discoin.eric', 'discoin.facuaraujo', 'discoin.ezequielcastillo', 'discoin.fedeadal', 'discoin.federic', 'discoin.ezequiel', 'discoin.fedec', 'discoin.ferchula', 'discoin.facujc', 'discoin.fernando', 'discoin.facundop', 'discoin.flavia', 'discoin.flavia1972', 'discoin.florenciamijailidis93', 'discoin.flor', 'discoin.alex', 'discoin.amakor', 'discoin.alu', 'discoin.ana.giambroni', 'discoin.anabelaciantino', 'discoin.anderrjara', 'discoin.andre.eme73', 'discoin.andrea', 'discoin.andres', 'discoin.anita196', 'discoin.angeles11', 'discoin.antopagani', 'discoin.ani.episcopo', 'discoin.ariel.lafuente', 'discoin.barbipiazza', 'discoin.ariel65536', 'discoin.aristoteles', 'discoin.belen', 'discoin.brunoch', 'discoin.belencita', 'discoin.carla', 'discoin.camilavega', 'discoin.carina', 'discoin.carola', 'discoin.chauchasub', 'discoin.carolina', 'discoin.chernobyl1986', 'discoin.cgf1976', 'discoin.crisceci0505', 'discoin.cnegrelli', 'discoin.cristin07silva', 'discoin.cuchuflurito', 'discoin.damian22', 'discoin.cuba7', 'discoin.daiana.m95', 'discoin.dantealta47', 'discoin.daniela', 'discoin.die', 'discoin.diegost', 'discoin.dmcarruego', 'discoin.diegote', 'discoin.dvszcehrykth', 'discoin.subacc1', 'discoin.edufol', 'discoin.eeveelynn1', 'discoin.eliseogirard', 'discoin.abel', 'discoin.adrian', 'discoin.acsirito', 'discoin.agus', 'discoin.agustin96', 'discoin.agustinbahl5', 'discoin.aldana', 'discoin.aleja', 'discoin.ale']
  for tmp in rpc.db_lookup_accounts(ACCOUNT_PREFIX , 500):
    if tmp[0].startswith(ACCOUNT_PREFIX) and tmp[0] not in _sent:
      i=i+1
      p = rpc.db_get_account_balances(tmp[1], [DISCOIN_ID])
      if try_int(p[0]['amount'])<=0:
        print(' -- #{0}'.format(i))
        print(json.dumps(tmp[0]))
        #print(json.dumps(p))
        do_airdrop('1', tmp[1], '101')
        print('DONE')

def do_process_airdrop2():
  i=0
  for tmp in rpc.db_lookup_accounts(ACCOUNT_PREFIX , 500):
    if tmp[0].startswith(ACCOUNT_PREFIX):
      p = rpc.db_get_account_balances(tmp[1], [DISCOIN_ID])
      if try_int(p[0]['amount'])<=0:
        # print(' -- #{0}'.format(i))
        # print(json.dumps(tmp))
        # print(json.dumps(p))
        do_send = True
        txs = rpc.history_get_relative_account_history(tmp[1])
        for tx in txs:
          #{u'virtual_op': 23543, u'trx_in_block': 43, u'block_num': 32343169, u'op_in_trx': 0, u'result': [0, {}], u'id': u'1.11.591379136', u'op': [0, {u'fee': {u'asset_id': u'1.3.4679', u'amount': 11}, u'from': u'1.2.1106071', u'memo': {u'nonce': 0, u'to': u'BTS1111111111111111111111111111111114T1Anm', u'message': u'7e72653a3130313a61697264726f70', u'from': u'BTS1111111111111111111111111111111114T1Anm'}, u'to': u'1.2.1123789', u'amount': {u'asset_id': u'1.3.4679', u'amount': 10100000}, u'extensions': []}]}
          if tx['result'][0]==0 and tx['result'][1]['amount']['amount']==10100000:
            do_send = False
            break 
        if do_send:
          i=i+1
          do_airdrop('1', tmp[1], '101')
          print(' -- sent to {0}:{1}'.format(tmp[0], tmp[1]))
  print('---- airdrop done! Q:{0}'.format(i))

if __name__ == '__main__':
  do_process_airdrop2()
  # do_airdrop('1', cache.get_account_id(u'discoin.airdroptester'), '101')
  # do_airdrop('1', cache.get_account_id(u'discoin.airdroptester2'), '1')
  
