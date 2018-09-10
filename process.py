import os

import traceback
import websocket
import thread
import time
from dateutil.parser import parse

import requests
import json
import rpc
import cache

from time import sleep
from utils import *
from tasks import *
from models import *
from ops_func import *

from bts2helper import *
from credit_func import set_overdraft, issue_reserve_fund #, multisig_set_overdraft

valid_assets = [DISCOIN_ACCESS_ID]

# def user_authorize_user(t):

#   to            = t.memo[8:].decode('hex')
#   to_id         = cache.get_account_id(unicode(ACCOUNT_PREFIX + to))
#   from_name     = real_name(t.from_name)
#   endorse_type  = t.amount_asset

#   if endorse_type not in valid_assets:
#     raise Exception('invalid_endorsement')

#   p = rpc.db_get_account_balances(to_id, [DESCUBIERTO_ID])
#   if p[0]['amount'] > 0:
#     raise Exception('already_have_credit')

#   if to_id in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']:
#     raise Exception('already_endorsed')

#   asset = rpc.db_get_assets([endorse_type])[0]
#   memo  = {
#     'message' : '~eb:{0}'.format(from_name).encode('hex')
#   }

#   tx = build_tx_and_broadcast(
#       transfer(
#         PROPUESTA_PAR_ID,
#         to_id,
#         asset,
#         1,
#         memo
#       ) + account_whitelist(
#         PROPUESTA_PAR_ID,
#         to_id,
#         2 #insert into black list
#       )
#     , None)

#   to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
#   signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
#   tx['signatures'] = [signature]

#   print tx
#   p = rpc.network_broadcast_transaction(tx)
#   return to_sign

def user_applies_authorization(t):
  
  print ('===========================================')
  print ("ENTER => user_applies_authorization")

  endorse_type  = t.amount_asset

  if endorse_type not in valid_assets:
    print (' == INVALID ASSET')
    raise Exception('invalid_endorsement')

  p = rpc.db_get_account_balances(t.from_id, [DISCOIN_CREDIT_ID])
  if p[0]['amount'] > 0:
    print (' == already_have_credit')
    raise Exception('already_have_credit')

  amount = t.amount
  
  accounts_to_issue = {
    t.from_name  : amount,
  }

  # HACK : poner las privadas en orden y los owner de los assets
#   multisig_set_overdraft(accounts_to_issue)
  print ("apply auth => about to apply overdraft")
  ret = set_overdraft(accounts_to_issue)
  
  # Validar que la TX llego a destino :(
  # accounts_to_issue
  # {"discoin.business2": 55000}
  # t.from_name  : amount
  with session_scope() as db:
    biz = db.query(Business).filter(Business.account==t.from_name).first()
    if not biz:
      print (' NO hay business ' + t.from_name)
      return
    biz_credit = BusinessCredit.from_process(biz.id, amount)
    db.add(biz_credit)
    db.commit()
    print (' Business Credit salvado ' + t.from_name)
    

    
def user_transfer_authorizations(t):
  
  to            = t.memo[8:].decode('hex')
  to_id         = cache.get_account_id(unicode(ACCOUNT_PREFIX + to))
  from_name     = real_name(t.from_name)
  endorse_type  = t.amount_asset

  if to_id in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']:
    raise Exception('unable_to_receive')

  asset = rpc.db_get_assets([endorse_type])[0]
  memo = {
    'message' : '~et:{0}'.format(from_name).encode('hex')
  }

  tx = build_tx_and_broadcast(
      transfer(
        PROPUESTA_PAR_ID,
        to_id,
        asset,
        t.amount,
        memo
      )
    , None)

  to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
  signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
  tx['signatures'] = [signature]

  print( json.dumps(tx))
  p = rpc.network_broadcast_transaction(tx)
  return to_sign

def system_issue_credit(business_credit, reserve_fund):
#   issue_reserve_fund(business_credit.business.account, business_credit.amount)
  print ('---- biz_credit', business_credit.amount)
  print (reserve_fund)
  amount = int(business_credit.amount)*int(reserve_fund)/100
  print (' **** system_issue_credit')
  print (DISCOIN_ADMIN_NAME)
  print (amount)
  issue_reserve_fund(DISCOIN_ADMIN_NAME, amount)
  print (' ** issued!')
  
def do_process_2():
  try:
    with session_scope() as db:
      q_conf, is_new  = get_or_create(db, NameValue, name  = 'configuration')
      
#       q_conf.airdrop.by_wallet.reward_amount
#       q_conf.airdrop.by_wallet.first_wallet_download
#       q_conf.airdrop.by_wallet.first_tx_reward_amount
#       print json.dumps(q_conf.value)
      reserve_fund = q_conf.value['reserve_fund']['new_business_percent']
#       print ' ** '
#       print reserve_fund
#       return
      q = db.query(BusinessCredit)
      q = q.filter(BusinessCredit.processed == 0)
      q = q.order_by(BusinessCredit.id)
      q = q.limit(10)
      for t in q.all():
        system_issue_credit(t, reserve_fund)
        t.processed = 1
        db.commit()

  except Exception as ex:
    print (str(ex))
    logging.error(traceback.format_exc())
    
def do_process():
  try:
    
    with session_scope() as db:
      q = db.query(Transfer)
      q = q.filter(Transfer.processed == 0)
      q = q.order_by(Transfer.id)
      q = q.limit(100)

      for t in q.all():

        last_err = None

        try:        
          # Operaciones de avales
#           if t.amount_asset in ALL_AVAL_TYPES and t.to_id == DISCOIN_ADMIN_ID:
          
          if t.amount_asset == DISCOIN_ACCESS_ID and t.to_id == DISCOIN_ADMIN_ID:
            print ('------')
            print (t.id)
            print (t.memo)

            txid = None
            # usuario1 transfiere a gobierno AVAL(i) con memo '~ie:nombre'
            # accion => autorizar a usuario (a.b.c)
#             if t.memo and t.memo[:8] == '~ie:'.encode('hex'):
#               txid = user_authorize_user(t)
              
            # usuario2 transfiere a gobierno AVAL(i) con memo '~ae'
            # accion => usuario2 quiere credito
            #el
            if t.memo and t.memo == '~ae'.encode('hex'):
              txid = user_applies_authorization(t)
            
            # usuario3 transfiere a gobierno AVAL(i) con memo '~et:nombre'
            # accion => usuario3 transfiere avales a usuario a.b.c
#             elif t.memo and t.memo[:8] == '~et:'.encode('hex'):
#               txid = user_transfer_authorizations(t)

            t.processed = 1
  
            if txid:
              last_err, ok = get_or_create(db, LastError, transfer_id=t.id)
              last_err.txid = txid
              last_err.description = 'ok'

            #db.add(last_err)
          
          # Otras transferencias
          else:
            t.processed = 1

        except Exception as ex:
          
          print ('******************************* %d' % t.id)
          print (traceback.format_exc())

          t.processed = -1
          last_err, ok = get_or_create(db, LastError, transfer_id=t.id)
          last_err.description = str(ex)
          db.add(last_err)

        finally:
          db.commit()

  except Exception as ex:
    print (str(ex))
    logging.error(traceback.format_exc())

if __name__ == "__main__":
  while True:
    try:
      do_process()
      sleep(3)
      do_process_2()
      sleep(3)
    except Exception as ex:
      logging.error(traceback.format_exc())
