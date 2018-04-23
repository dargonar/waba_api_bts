# coding: utf-8
import os
import sys
import logging
import traceback
import time

from datetime import datetime, timedelta
from decimal import Decimal

from flask import Flask, jsonify, make_response, request, g
from flask_graphql import GraphQLView
from flask_cors import CORS, cross_origin

from schema_v3 import theSchema
from utils import *

from models import *
Base.metadata.create_all(get_engine())

from datatables import ColumnDT, DataTables

from ops import *
from ops_func import *
from bts2helper import *
import simplejson as json
from graphql.execution.executors.gevent import GeventExecutor
#from graphql.execution.executors.thread import ThreadExecutor

#ACCOUNT_PREFIX = '' 
from memcache import Client
import rpc
import cache

import init_model

ERR_UNKNWON_ERROR    = 'unknown_error'

REGISTER_PRIVKEY = '5JQGCnJCDyraociQmhDRDxzNFCd8WdcJ4BAj8q1YDZtVpk5NDw9'

wifs = { 
          'discoin.biz1' : '5J1DdLRTrwxYxFih33A8wgxRLE7hqTz6Te58ES94kqJEBsMuH3B',
          '1.2.21'       : '5J1DdLRTrwxYxFih33A8wgxRLE7hqTz6Te58ES94kqJEBsMuH3B',
          'discoin.biz2' : '5JaAXXB9jMEVSVEyX6DQSskQhqXRr67HwZ1jLPwHyysPWQtuZgR',
          '1.2.22'       : '5JaAXXB9jMEVSVEyX6DQSskQhqXRr67HwZ1jLPwHyysPWQtuZgR',
          'discoin.biz3' : '5Kjz35R9W3m5ZpznZMSpdySz35tZsXZbzsuSdbtV12YC9Zaxzd9',
          '1.2.25'       : '5Kjz35R9W3m5ZpznZMSpdySz35tZsXZbzsuSdbtV12YC9Zaxzd9',
          'discoin.biz4' : '5JqmMaoHucyZPNQjBdwyVPd5vmvECD57cbZU4zNY9KMcFULDUrH',
          '1.2.26'       : '5JqmMaoHucyZPNQjBdwyVPd5vmvECD57cbZU4zNY9KMcFULDUrH'
       }


def create_app(**kwargs):
  app = Flask(__name__)
  app.debug = True
  app.add_url_rule('/graphql/v3', view_func=GraphQLView.as_view('graphql', schema=theSchema, **kwargs))

  @app.before_request
  def log_request():
    print request.data
  
  @app.before_request
  def before_request():
    g.start = time.time()
  
  @app.teardown_request
  def teardown_request(exception=None):
    diff = time.time() - g.start
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
    print 'EL REQUEST TOTAL TOMO =>', diff
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
    
  CORS(app)
    
  return app

if __name__ == '__main__':
  app = create_app(executor=GeventExecutor(), graphiql=True)
  
  @app.errorhandler(Exception)
  def unhandled_exception(e):
    return make_response(jsonify({'error': str(e)}), 500)
  
  @app.route('/api/v3/dashboard/kpis', methods=['POST', 'GET'])
  def dashboard_kpis():
    
    main_asset = rpc.db_get_assets([DISCOIN_ID])
    users      = rpc.db_get_asset_holders_count(DISCOIN_ID)
    
    _now = datetime.utcnow()
    
    return jsonify( 
        {
          'updated_at': str(_now),
          'main_asset':main_asset,
          'airdrop': {
            'issued': 1500,
            'max_supply': 10000000,
            'tx_quantity': 1524,
            'max_tx_quantity': 100000
          },
          'businesses': {
            'quantity': {
              'by_status': {
                'ok': 582,
                'yellow': 452,
                'red': 556,
                'out': 10
              },
              'by_initial_credit': [
                {
                  'initial_credit': 10000,
                  'quantity': 15
                },
                {
                  'initial_credit': 15000,
                  'quantity': 50
                },
                {
                  'initial_credit': 20000,
                  'quantity': 36
                }
              ],
            'new_businesses': [
              {
                'quantity': '15000',
                'timestamp': str(_now + timedelta(days=-1))
              },
              {
                'quantity': '15001',
                'timestamp': str(_now + timedelta(days=-2))
              },
              {
                'quantity': '15002',
                'timestamp': str(_now + timedelta(days=-3))
              },
            ]
          },
          'transactions': {
            'total_quantity': '15230000',
            'daily': [{
                'quantity': '15000',
                'timestamp': str(_now + timedelta(days=-1))
              },
              {
                'quantity': '15001',
                'timestamp': str(_now + timedelta(days=-2))
              },
              {
                'quantity': '15002',
                'timestamp': str(_now + timedelta(days=-3))
              },
            ]
          },
          'users': {
            'holders': users,
            'registered': users,
            'new_users': [{
                'quantity': '15000',
                'timestamp': str(_now + timedelta(days=-1))
              },
              {
                'quantity': '15001',
                'timestamp': str(_now + timedelta(days=-2))
              },
              {
                'quantity': '15002',
                'timestamp': str(_now + timedelta(days=-3))
              },
            ]
          }
        }
      } 
    )
    
  @app.route('/api/v3/dashboard/configuration', methods=['POST', 'GET'])
  def dashboard_configuration():
    if request.method=='GET':
      nm = None
      with session_scope() as db:
        #ret = db.query(NameValue).filter(NameValue.name=='configuration').first()
        nm, is_new = get_or_create(db, NameValue, name  = 'configuration')
        if is_new:
          nm.value = init_model.get_default_configuration()
        db.expunge(nm)
      
      asset_balance, asset_overdraft, asset_invite = rpc.db_get_assets([DISCOIN_ID, DISCOIN_CREDIT_ID, DISCOIN_ACCESS_ID])
      
      asset_balance['key']    = 'balance'
      asset_overdraft['key']  = 'descubierto' 
      asset_invite['key']     = 'invitado'
      assets                  = {'asset_balance':asset_balance, 'asset_overdraft':asset_overdraft, 'asset_invite':asset_invite}
      return jsonify( { 'configuration': nm.value if nm.value else '', 'assets' : assets, 'updated_at' : nm.updated_at } );
    
    if request.method=='POST':
      # ToDo: chequear y guardar configuration set.
      return jsonify( {'method':request.method} );
  
  @app.route('/api/v3/dashboard/categories', methods=['POST', 'GET'])
  def dashboard_categories():
    if request.method=='GET':
      nm = None
      with session_scope() as db:
        #ret = db.query(NameValue).filter(NameValue.name=='configuration').first()
        nm, is_new = get_or_create(db, NameValue, name  = 'categories')
        if is_new:
          nm.value = init_model.get_default_categories()
        db.expunge(nm)
      return jsonify( { 'categories': nm.value if nm.value else '', 'updated_at' : nm.updated_at } );
    
    if request.method=='POST':
      # ToDo: chequear y guardar configuration set.
      return jsonify( {'method':request.method} );
    
  @app.route('/api/v3/dashboard/business/list/<with_balance>/<skip>/<count>', methods=['GET'])
  def dashboard_business(with_balance, skip, count):
#     init_model.init_categories()
#     init_model.init_businesses()
#     init_model.init_discount_schedule()
    
    # TODO: procesar cada comercio, y listar tambien montos refunded(out) y discounted (in), historicos
    with session_scope() as db:
      return jsonify( { 'businesses': [ build_business(x) for x in db.query(Business).all()] } );
  
  def build_business(biz):
    business = biz.to_dict()
    business['balances'] = get_business_balances(biz.account_id)
    return business
  
  def get_business_balances(account_id):
    assets = [DISCOIN_ID, DISCOIN_CREDIT_ID, DISCOIN_ACCESS_ID]
    p = rpc.db_get_account_balances(account_id, assets)
    the_assets = {}
    for x in assets:
      the_assets[x] = cache.get_asset(x)
    x = {
      'balance'         : next(( amount_value(x['amount'], the_assets[x['asset_id']]) for x in p if x['asset_id'] == DISCOIN_ID), None), 
      'initial_credit'  : next(( amount_value(x['amount'], the_assets[x['asset_id']]) for x in p if x['asset_id'] == DISCOIN_CREDIT_ID), None), 
      'ready_to_access' : next(( amount_value(x['amount'], the_assets[x['asset_id']]) for x in p if x['asset_id'] == DISCOIN_ACCESS_ID), None)
    }
    print '================================== get_business_balances #3'
    return x
    
  @app.route('/api/v3/dashboard/business/profile/<account_id>/load', methods=['GET'])
  def dashboard_business_profile(account_id):
    with_balance = "1" 
    with session_scope() as db:
      return jsonify( { 'business': db.query(Business).filter(Business.account_id==account_id).first().to_dict(str2bool(with_balance))} );
  
  
  @app.route('/api/v3/dashboard/business/profile/<account_id>/update', methods=['GET', 'POST'])
  def dashboard_update_business_profile(account_id):
    # curl -H "Content-Type: application/json" -X POST -d '{  "business": {    "address": null,    "category_id": 1,    "description": "Larsen",    "discount_schedule": [{  "id"        : 1,  "date"      : "monday",  "discount"  : 30},{  "id"        : 1,  "date"      : "tuesday",  "discount"  : 20}],    "image": null,    "latitude": null,    "location": null,    "longitude": null,    "name": "Larsen",    "subcategory_id": 2  },  "secret": "secrettext_1.2.26"}' http://35.163.59.126:8080/api/v3/dashboard/business/profile/1.2.26/update
    # curl -H "Content-Type: application/json" -X POST -d '{  "business": {    "address": null,    "category_id": 1,    "description": "Larsen",    "discount_schedule": [{  "id"        : 1,  "date"      : "monday",  "discount"  : 30},{  "id"        : 1,  "date"      : "tuesday",  "discount"  : 20}],    "image": null,    "latitude": -22.36,    "location": null,    "longitude": -33.36,    "name": "Larsen",    "subcategory_id": 2  },  "secret": "secrettext_1.2.26"}' http://35.163.59.126:8080/api/v3/dashboard/business/profile/1.2.26/update
    secret_text = 'secrettext_'
    if request.method=='GET':
      the_secret_text = secret_text + account_id
      with session_scope() as db:
        return jsonify( { 'business': db.query(Business).filter(Business.account_id==account_id).first().to_dict_for_update(), 'secret' : the_secret_text } );
    
#     try:
      
    biz_json           = request.json.get('business')
    signed_secret      = request.json.get('signed_secret')
#       owner           = str( biz_json.get('owner', '') )
#       active          = str( biz_json.get('active', '') )
#       memo            = str( biz_json.get('memo', '') )

    with session_scope() as db:
      biz = db.query(Business).filter(Business.account_id==account_id).first()
      if not biz:
        return jsonify( { 'error' : 'account_id_not_found'} )
#         # Elimino la tabla de descuentos del negocio.
#         db.query(DiscountSchedule).filter(DiscountSchedule.business_id==account_id).delete(synchronize_session='fetch')
      errors = biz.validate_dict(biz_json, db)
      if len(errors)>0:
        return jsonify( { 'error' : 'errors_occured', 'error_list':errors } )

      biz.discount_schedule[:] = []
      biz.from_dict_for_update(biz_json)
      db.add(biz)
      for schedule in biz_json.get('discount_schedule', []):
        dis_sche = DiscountSchedule()
        try:
          dis_sche.from_dict(biz.id, schedule)
        except Exception as e:
          errors.append({'field':'discount_schedule', 'error':str(e)})
        db.add(dis_sche)
      if len(errors)>0:
        db.rollback()
        return jsonify( { 'error' : 'errors_occured', 'error_list':errors } )
      db.commit()

#       return jsonify({'tx' : tx})
    return jsonify({'ok':'ok'})

#     except Exception as e:
#       logging.error(traceback.format_exc())
#       return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)
    
#   @app.route('/api/v3/overdraft/invite', methods=['POST'])
#   def invite_overdraft():
#     business_name   = request.json.get('business_name')  
#     initial_credit  = request.json.get('initial_credit')    
#     business_id     = cache.get_account_id(business_name)
  
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # Subaccount Management
  # =================================================================================================
  
  @app.route('/api/v3/dashboard/business/<account_id>/subaccount/list/<start>', methods=['GET', 'POST'])
  def dashboard_business_account_list(account_id, start):
    print ' == get_withdraw_permissions_by_giver:'
    res = rpc.db_get_withdraw_permissions_by_giver(account_id, start, 100)
    print json.dumps(res, indent=2)
#     res = rpc.db_get_withdraw_permissions_by_recipient(business_id, '1.12.0', 100)
    
    return jsonify( {'subaccounts':res} )

  
  @app.route('/api/v3/business/subaccount/add_or_update/create', methods=['POST'])
  def subaccount_add_or_update_create():
    
    # curl -H "Content-Type: application/json" -X POST -d '{"business_id" : "1.2.25", "subaccount_id" : "1.2.27", "limit" : "2000", "_from" : null, "period" : null, "periods" : 365}' http://35.163.59.126:8080/api/v3/business/subaccount/add_or_update/create    business_id     = request.json.get('business_id')  
    subaccount_id   = request.json.get('subaccount_id')  
    limit           = request.json.get('limit')
    _from           = request.json.get('from')
    period          = request.json.get('period')
    periods         = request.json.get('periods')

    tx = subaccount_add_or_update_create_impl(business_id, subaccount_id, limit, _from, period, periods)
    
    return jsonify( {'tx':tx} )
  
  def subaccount_add_or_update_create_impl(business_id, subaccount_id, limit, _from, period, periods):
    
    # Check if business has credit.
    p = rpc.db_get_account_balances(business_id, [DISCOIN_CREDIT_ID])
    if p[0]['amount'] <= 0:
      return jsonify({'error':'account_has_no_credit'})
    print ' ======================================================'
    print ' ====== subaccount_add_or_update_create_impl #1'
    # Check if subaccount is valid account.
    subaccounts = rpc.db_get_accounts([subaccount_id])
    print ' ======================================================'
    print ' ====== subaccount_add_or_update_create_impl #2'
    # rpc.db_get_accounts(['1.2.18'])
    if not subaccounts or len(subaccounts)==0:
      return jsonify( {'error': 'subaccount_not_exists'} )
          
    print ' ======================================================'
    print ' ====== subaccount_add_or_update_create_impl #3'
    asset, asset_core = rpc.db_get_assets([DISCOIN_ID, CORE_ASSET])
    
    # ~ie:<%y%m%d>:<1.2.1526>:25000
    if not _from:
#       _from = datetime.utcnow().strftime('%y%m%d')
      _from = (datetime.utcnow()+timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%S')
#       _from = '2018-04-24T00:00:00'
    if not period:
      period = 86400 # 1 day in seconds
    if not periods:
      periods = 365 # 365 periods = 1 year
    
    print ' ======================================================'
    print ' ====== subaccount_add_or_update_create_impl #4'
    my_amount = reverse_amount_value(limit, asset)
    my_amount_asset = {
      'amount'  : int(my_amount),
      'asset'   : DISCOIN_ID
    }
    withdraw_permission_op = withdraw_permission_create(business_id, subaccount_id, my_amount_asset, period, periods, _from, None, CORE_ASSET)
    
    print ' == withdraw_permission_op: '
    print withdraw_permission_op
    
    fees = rpc.db_get_required_fees([withdraw_permission_op[0]] , CORE_ASSET)
    
    print ' == fees: '
    print fees
    
    _transfer = transfer(
        DISCOIN_ADMIN_ID,
        business_id,
        asset_core,
        amount_value(fees[0]['amount'], asset_core)
      )
    print ' == transfer: '
    print _transfer
    
    print ' ======================================================'
    print ' ====== subaccount_add_or_update_create_impl #5'
    
#     _transfer +
    tx = build_tx_and_broadcast(
      _transfer + [withdraw_permission_op[0]] 
    , None)
    
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    tx['signatures'] = [signature]
    return tx

  @app.route('/api/v3/business/subaccount/add_or_update/create/broadcast', methods=['POST'])
  def subaccount_add_or_update_create_and_broadcast():
    
    # curl -H "Content-Type: application/json" -X POST -d '{"business_id" : "1.2.25", "subaccount_id" : "1.2.27", "limit" : "2000", "_from" : null, "period" : null, "periods" : 365}' http://35.163.59.126:8080/api/v3/business/subaccount/add_or_update/create/broadcast
    # curl -H "Content-Type: application/json" -X POST -d '{"business_id" : "1.2.25", "subaccount_id" : "1.2.28", "limit" : "2000", "_from" : null, "period" : null, "periods" : 365}' http://35.163.59.126:8080/api/v3/business/subaccount/add_or_update/create/broadcast
      
    business_id     = request.json.get('business_id')  
    subaccount_id   = request.json.get('subaccount_id')  
    limit           = request.json.get('limit')
    _from           = request.json.get('from')
    period          = request.json.get('period')
    periods         = request.json.get('periods')
    
    # ToDo:
    # Si ya tiene permiso, hay que tirar el update:
#     [
#       26,{
#         "fee": {
#           "amount": 0,
#           "asset_id": "1.3.0"
#         },
#         "withdraw_from_account": "1.2.0",
#         "authorized_account": "1.2.0",
#         "permission_to_update": "1.12.0",
#         "withdrawal_limit": {
#           "amount": 0,
#           "asset_id": "1.3.0"
#         },
#         "withdrawal_period_sec": 0,
#         "period_start_time": "1970-01-01T00:00:00",
#         "periods_until_expiration": 0
#       }
#     ]

    tx = subaccount_add_or_update_create_impl(business_id, subaccount_id, limit, _from, period, periods)
    
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    
    signature = bts2helper_sign_compact(to_sign, wifs[business_id])
    
    if not tx['signatures']: tx['signatures'] = []
    tx['signatures'].append(signature);    
    
    # como listamos los permisos? -> get_account_history_by_operations discoin.biz3 [25] 0 100 ??
    # como testeamos el permiso?  -> transfer discoin.biz4.subaccount1 discoin.biz4.subaccount2 10000 THEDISCOIN.M "ehhh" true

    res = rpc.network_broadcast_transaction_sync(tx)
    print json.dumps(res, indent=2)
    return jsonify( {'res':res} )
  
  # ToDo:  
  # withdraw_permission_claim_operation
  #     [
  #       27,{
  #         "fee": {
  #           "amount": 0,
  #           "asset_id": "1.3.0"
  #         },
  #         "withdraw_permission": "1.12.0",
  #         "withdraw_from_account": "1.2.0",
  #         "withdraw_to_account": "1.2.0",
  #         "amount_to_withdraw": {
  #           "amount": 0,
  #           "asset_id": "1.3.0"
  #         }
  #       }
  #     ]
  
#   def multisig_change_keys(account, owner, active, memo_key):
#     init([account])

#     active_auth = {
#       'weight_threshold' : 1,
#       'account_auths'    : [],
#       'key_auths'        : [[active,1]], 
#       'address_auths'    : []
#     }

#     owner_auth = {
#       'weight_threshold' : 1,
#       'account_auths'    : [[account_id('discoin.admin'),1]],
#       'key_auths'        : [[owner,1]], 
#       'address_auths'    : []
#     }

#     ops = account_update(
#       account_id(account), 
#       owner_auth, 
#       active_auth, 
#       {'memo_key':memo_key},
#       [wifs['discoin.admin']],
#       assets['DISCOIN']['id']
#     )

  @app.route('/api/v3/business/endorse/create', methods=['POST'])
  def endorse_create():
    # TEST: curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz1","initial_credit":"10000"}' http://35.163.59.126:8080/api/v3/business/endorse/create
    
    business_name   = request.json.get('business_name')  
    initial_credit  = request.json.get('initial_credit')

    tx = endorse_create_impl(business_name, initial_credit)
    
    return jsonify( {'tx':tx} )
  
  def endorse_create_impl(business_name, initial_credit):
    
    business_id     = cache.get_account_id(business_name)
    #     from_id        = cache.get_account_id(ACCOUNT_PREFIX + _from)
    #     DISCOIN_ADMIN_ID = '1.2.18'
    #     DISCOIN_ID
    #     DISCOIN_CREDIT_ID   = '1.3.2' # DESCUBIERTO 
    #     DISCOIN_ACCESS_ID   = '1.3.3' # ENDORSEMENT
    
    print ' ======================================================'
    print ' ====== XX endorse_create_impl #1'
    # TODO: utilizar el sender(to) en vez de DISCOIN_ADMIN_ID.
    # Check if admin account has access tokens.
    p = rpc.db_get_account_balances(DISCOIN_ADMIN_ID, [DISCOIN_ACCESS_ID])
    if p[0]['amount'] == 0:
      return jsonify({'error':'no_endorsement_available'})
    
    print ' ======================================================'
    print ' ====== XX endorse_create_impl #2'
    # Check if business has credit.
    p = rpc.db_get_account_balances(business_id, [DISCOIN_CREDIT_ID])
    if p[0]['amount'] > 0:
      return jsonify({'error':'already_have_credit'})
    
    print ' ======================================================'
    print ' ====== XX endorse_create_impl #3'
    p = rpc.db_get_account_balances(business_id, [DISCOIN_ACCESS_ID])
    if p[0]['amount'] > 0:
      return jsonify({'error':'already_have_endorsement'})

    print ' ======================================================'
    print ' ====== XX endorse_create_impl #4'
    asset, asset_core = rpc.db_get_assets([DISCOIN_ACCESS_ID, CORE_ASSET])
    
    # ~ie:<%y%m%d>:<1.2.1526>:25000
    utc_now = datetime.utcnow().strftime('%y%m%d')
    memo = {
      'message' : '~ie:{0}:{1}:{2}'.format(utc_now, business_id, initial_credit).encode('hex')
    }
    
    print ' ======================================================'
    print ' ====== XX endorse_create_impl #5'
    # transfer_op(_from, _to, amount, memo=None, fee=None)
    # get_prototype_operation transfer_operation
    # get_prototype_operation withdraw_permission_update_operation
    # get_prototype_operation withdraw_permission_claim_operation
#     endorse_transfer_op = transfer_op()
    endorse_transfer_op = transfer(DISCOIN_ADMIN_ID, business_id, asset, initial_credit, memo, None, CORE_ASSET)
    # def transfer(from_id, to_id, asset, amount, memo=None, wif=None, pay_in=CORE_ASSET):
    
    # Para ver prototipos de TXs ver http://docs.bitshares.org/bitshares/tutorials/construct-transaction.html 

    print ' ======================================================'
    print ' ====== XX endorse_create_impl #6'
    #get_prototype_operation account_whitelist_operation
    tx = build_tx_and_broadcast(
      account_whitelist(
        DISCOIN_ADMIN_ID,
        business_id,
        0 #remove from black list
      ) 
      + [endorse_transfer_op[0]] 
      + account_whitelist(
        DISCOIN_ADMIN_ID,
        business_id,
        2 #add to black list
      )
    , None)
    
    print ' ======================================================'
    print ' ====== XX endorse_create_impl #7'
    print ' ======================================================'
    
    return tx
  
  @app.route('/api/v3/business/endorse/create/broadcast', methods=['POST'])
  def endorse_create_and_broadcast():
    # TEST: curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz3","initial_credit":"12500"}' http://35.163.59.126:8080/api/v3/business/endorse/create/broadcast
    business_name   = request.json.get('business_name')  
    initial_credit  = request.json.get('initial_credit')
#     op_id           = request.json.get('op_id')
    print ' ======================================================'
    print ' ====== endorse_create_and_broadcast #1'
    
    tx  = endorse_create_impl(business_name, initial_credit)
    
    print ' ======================================================'
    print ' ====== endorse_create_and_broadcast #2'
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    
    print ' ======================================================'
    print ' ====== endorse_create_and_broadcast #3'
    signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    tx['signatures'] = [signature]
    
    res = rpc.network_broadcast_transaction_sync(tx)
    print json.dumps(res, indent=2)
    return jsonify( {'res':res} )
  
  @app.route('/api/v3/business/endorse/apply', methods=['POST'])
  def endorse_apply():
    
    business_name   = request.json.get('business_name')  
    initial_credit  = request.json.get('initial_credit')

    tx = endorse_apply_impl(business_name, initial_credit)
    return jsonify( {'tx':tx} )
    
  def endorse_apply_impl(business_name):
    
    business_id = cache.get_account_id(business_name)

    access_balance = rpc.db_get_account_balances(business_id, [DISCOIN_ACCESS_ID])
    if access_balance[0]['amount'] == 0:
      return jsonify({'error':'no_endorsement_available'})

    if business_id not in rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['blacklisted_accounts']:
      return jsonify({'error':'no_endore_state'})

    p = rpc.db_get_account_balances(business_id, [DISCOIN_CREDIT_ID])
    if p[0]['amount'] > 0:
      return jsonify({'error':'already_have_credit'})

    asset, asset_core = rpc.db_get_assets([DISCOIN_ACCESS_ID, CORE_ASSET])
    
    memo = {
      'message' : '~ae'.encode('hex')
    }

    apply_transfer_op = transfer(
      business_id,
      DISCOIN_ADMIN_ID,
      asset,
      access_balance[0]['amount'],
      memo,
      None,
      CORE_ASSET
    )[0]

    print "************************************************"
    print json.dumps(apply_transfer_op, indent=2)
    print "*********************"

    # fees = rpc.db_get_required_fees([endorse_transfer_op], CORE_ASSET)
    print "toma => ", apply_transfer_op[1]['fee']['amount']
    print "************************************************"

    tx = build_tx_and_broadcast(
      account_whitelist(
        DISCOIN_ADMIN_ID,
        business_id,
        0 #remove from black list
      ) + transfer(
        DISCOIN_ADMIN_ID,
        business_id,
        asset_core,
        amount_value(apply_transfer_op[1]['fee']['amount'], asset_core)
      ) + [apply_transfer_op] + account_whitelist(
        DISCOIN_ADMIN_ID,
        business_id,
        2 #add to black list
      )
    , None)

    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    tx['signatures'] = [signature]
    return tx #jsonify( {'tx':tx} )
  
  @app.route('/api/v3/business/endorse/apply/broadcast', methods=['POST'])
  def endorse_apply_and_broadcast():
    # TEST: 
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz1","initial_credit":"10000"}' http://35.163.59.126:8080/api/v3/endorse/apply/broadcast
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz2","initial_credit":"15000"}' http://35.163.59.126:8080/api/v3/endorse/apply/broadcast
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz3","initial_credit":"12500"}' http://35.163.59.126:8080/api/v3/endorse/apply/broadcast
    business_name   = request.json.get('business_name')  
    initial_credit  = request.json.get('initial_credit')
    
#     op_id           = request.json.get('op_id')
    print ' ======================================================'
    print ' ====== endorse_apply_and_broadcast #1'
    
#     tx  = endorse_apply_impl(business_name, initial_credit)
    tx  = endorse_apply_impl(business_name)
    
    print ' ======================================================'
    print ' ====== endorse_apply_and_broadcast #2'
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    
    print ' ======================================================'
    print ' ====== endorse_apply_and_broadcast #3'
    signature = bts2helper_sign_compact(to_sign, wifs[business_name])
    
    if not tx['signatures']: tx['signatures'] = []
    tx['signatures'].append(signature);
    
    res = rpc.network_broadcast_transaction_sync(tx)
    print json.dumps(res, indent=2)
    return jsonify( {'res':res} )
  
  @app.route('/api/v3/business/category', methods=['GET'])
  def business_category():
    # http://35.163.59.126:8080/api/v3/business/category?search=&cat_level=-1
    # ToDo: cachear! y romper cache on ABM de categoria.
    
    search        = request.args.get('search', '').strip()
    cat_level     = try_int(request.args.get('cat_level', 0))
    # -1: None
    # 0: Root (parent_id==None)
    # >0: Parent category id -> list its Subcats
    # List subcategories of a given root category.
    data=[]
    print ' ============== about to query categories'
    with session_scope() as db:
      q2 = db.query(Category)
      if len(search)>0:
        my_search = '%'+search+'%'
        print ' ============== search:'
        print search
        print my_search
        my_or = or_(Category.name.like(my_search), Category.description.like(my_search))
        q2 = q2.filter(my_or)
      if cat_level==1:
        q2 = q2.filter(Category.parent_id==None)
      if cat_level==0:
        q2 = q2.filter(Category.parent_id==None)
      if cat_level>0:
        q2 = q2.filter(Category.parent_id==cat_level)
      q2.order_by(Category.name).order_by(Category.description)
      print ' ============== cat_level:'
      print cat_level
      data = [ {'id' : c.id, 'name': c.name, 'description': c.description, 'parent_id': c.parent_id} for c in q2.all()] 
      print ' ============== query result:'
      print json.dumps(data)
      print ' ============== END!'
    return jsonify( {"categories":data} )
  
#   select * from  category where isnull(parent_id) order by name desc;

  @app.route('/api/v3/push_id', methods=['POST'])
  def push_id():
    # curl -H "Content-Type: application/json" -X POST -d '{"name":"fake.name","push_id":"qwertyasdfg"}' http://35.163.59.126:8080/api/v3/push_id
    with session_scope() as db:
      pi, is_new = get_or_create(db, PushInfo,
        name  = request.json.get('name'),
      )
      pi.push_id = request.json.get('push_id')
      pi.updated_at = datetime.utcnow()
      db.add(pi)
      db.commit()
    return jsonify( {'res':'ok'} )

  @app.route('/api/v3/push_tx', methods=['POST'])
  def push_tx():
    tx  = request.json.get('tx')
    if not tx:
      tx = request.json
      
    res = rpc.network_broadcast_transaction_sync(tx)
    print json.dumps(res, indent=2)
    return jsonify( {'res':res} )

#   @app.route('/api/v3/get_global_properties', methods=['GET'])
#   def db_get_global_properties():
#     return jsonify( rpc.db_get_global_properties() )

#   @app.route('/api/v3/welcome', methods=['GET'])
#   def welcome():
#     props = rpc.db_get_global_properties()
#     asset = rpc.db_get_assets([ASSET_ID])[0]
#     return jsonify({'props':props, 'asset':asset})


  @app.route('/api/v3/account/find', methods=['POST'])
  def find_account():
    # OLD find_account
    
    # TEST: curl -H "Content-Type: application/json" -X POST -d '{"key":"BTS5NQUTrdEgKH4fz5L5DLJZBSkdLWUY4CfnaNZ77yvZAnUZNC89d"}' http://35.163.59.126:8080/api/v3/account/find
    
    print ' ========================== Find Account by PubKey'
    key  = request.json.get('key')
    account_ids = set(rpc.db_get_key_references([key])[0])
    print ' == account_ids : '
    print account_ids
    res = [real_name(a['name']) for a in rpc.db_get_accounts(list(account_ids))]
    print ' == res : '
    print json.dumps(res) 
    return jsonify({"res" : res})

  @app.route('/api/v3/account/by_name/<account>', methods=['GET'])
  def get_account(account):
  
    # TEST: http://35.163.59.126:8080/api/v3/account/by_name/
#     if str(account) != str('gobierno-par'):
#     print '================= get_account'
#     print account
    if str(account) != str(DISCOIN_ADMIN_NAME):
#       print '================= get_account #1'
      if not account.startswith(ACCOUNT_PREFIX):
#         print '================= get_account #2'
        account = ACCOUNT_PREFIX+account
#     print '================= get_account #3'
    res = rpc.db_get_account_by_name(account)
    if not res:
      return jsonify(  {'res': 'account_not_found', 'error':1})
    return jsonify( {"res": res}  )
  
  @app.route('/api/v3/account/search', methods=['GET'])
  def search_account():
    # OLD searchAccount
    search = request.args.get('search', '')
    search_filter = try_int(request.args.get('search_filter',0))
  
    # --------------------------------------------------- #
    # search_filter:
    #   0 = ALL
    #   1 = NO_CREDIT && NO_BLACK
    #   2 = HAS_CREDIT
    # --------------------------------------------------- #
    
    res = []
    for tmp in rpc.db_lookup_accounts(ACCOUNT_PREFIX + search, 10):
      if tmp[0].startswith(ACCOUNT_PREFIX):
        tmp[0] = tmp[0][len(ACCOUNT_PREFIX):]

        #print tmp[0], search
        if tmp[0].startswith(search):
          
          add_account = True
          print '=== Account: '
          print tmp[0]
          # Only with no-credit and no black-listed
          if search_filter == 1:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
            print '=== Overdraft: '
            print p[0]['amount']
            no_credit = p[0]['amount'] == 0
            no_black = tmp[1] not in rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['blacklisted_accounts']
            add_account = no_credit and no_black
          
          # Only with credit
          if search_filter == 2:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
            has_credit = p[0]['amount'] > 0
            #no_black = tmp[1] not in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']
            add_account = has_credit
          print '==============='
          if add_account:
            tmp[0] = ACCOUNT_PREFIX + tmp[0]
            res.append( tmp )

    return jsonify( {'res' : res} )

  @app.route('/api/v3/account/register', methods=['POST'])
  def account_register():
    # register_account name, owner_pubkey, active_pubkey, registrar_account, referrer_account, referrer_percent, broadcast
    try:
      req = request.json
      name   = ACCOUNT_PREFIX + str( req.get('name') )
      
      if req.get('secret') == 'cdc1ddb0cd999dbc5ba8d7717e3837f5438af8198d48c12722e63a519e73a38c':
        name = str( req.get('name') )
        
      owner  = str( req.get('owner') )
      active = str( req.get('active') )
      memo   = str( req.get('memo') )
      
      if not bts2helper_is_valid_name(name):
        return jsonify({'error': 'is_not_valid_account_name'})

      if not bts2helper_is_cheap_name(name):
        return jsonify({'error': 'is_not_cheap_account_name'})

      acc = rpc.db_get_account_by_name(name)
      if acc is not None:
        return jsonify({'error': 'already_taken_account_name'})

      rop = register_account_op(
        DISCOIN_ADMIN_ID, 
        DISCOIN_ADMIN_ID, 
        10000, 
        name, 
        {
          'weight_threshold' : 1,
          'account_auths'    : [[DISCOIN_ADMIN_ID,1]],
          'key_auths'        : [[owner,1]], 
          'address_auths'    : []
        },
        {
          'weight_threshold' : 1,
          'account_auths'    : [],
          'key_auths'        : [[active,1]], 
          'address_auths'    : []
        },
        memo, 
        DISCOIN_ADMIN_ID,
      )
      rop[1]['fee'] = rpc.db_get_required_fees([rop], '1.3.0')[0]
      
      ref_block_num, ref_block_prefix = ref_block(rpc.db_get_dynamic_global_properties()['head_block_id'])

      tx = build_tx([rop], ref_block_num, ref_block_prefix)

      #print tx
      to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)

      wif = REGISTER_PRIVKEY
      #signature = sign_compact2(to_sign, b.encode_privkey(k, 'wif'))
      signature = bts2helper_sign_compact(to_sign, wif)

      tx['signatures'] = [signature]
      p = rpc.network_broadcast_transaction_sync(tx)
      print json.dumps(p, indent=2)
      return jsonify({'ok':'ok', 'res':p})

    except Exception as e:
      logging.error(traceback.format_exc())
      return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)

  @app.route('/api/v3/business/register', methods=['POST'])
  def business_register():
    
    # curl -H "Content-Type: application/json" -X POST -d '{"account_name":"discoin.biz4", "owner":"BTS6FvvuMeoZp2v4QFMZyHLBtW79qNih979DsWnNJDNsaPHUYaaav", "active":"BTS82ZonBP7JKUdau4tink8Ui9vLBdbCUVh7dYgYPSA5wjDyXXGsK", "memo":"BTS6mAm8eoYLX4tGE3pMYujyvm2xpRCk74S5jSm5gviQ4yunLm6gj", "name" : "Larsen", "email" : "larsen@gmail.com", "telephone" : "+5491131272458", "category_id" : 1, "subcategory_id": 2}' http://35.163.59.126:8080/api/v3/business/register 

    try:
      req   = request.json
      account_name  = str( req.get('account_name') )
      if not account_name.startswith(ACCOUNT_PREFIX):
        account_name  = ACCOUNT_PREFIX + account_name
      
      if req.get('secret') == 'cdc1ddb0cd999dbc5ba8d7717e3837f5438af8198d48c12722e63a519e73a38c':
        account_name = str( req.get('account_name') )
        
      owner  = str( req.get('owner') )
      active = str( req.get('active') )
      memo   = str( req.get('memo') )
      
      if not bts2helper_is_valid_name(account_name):
        return jsonify({'error': 'is_not_valid_account_name'})

      if not bts2helper_is_cheap_name(account_name):
        return jsonify({'error': 'is_not_cheap_account_name'})

      acc = rpc.db_get_account_by_name(account_name)
      if acc is not None:
        return jsonify({'error': 'already_taken_account_name'})
      
      
      name            = str( req.get('name') )
      email           = str( req.get('email') )
      telephone       = str( req.get('telephone') )
      category_id     = str( req.get('category_id') )
      subcategory_id  = str( req.get('subcategory_id') )
      
      print '================== category_id'
      print category_id
      print '================== subcategory_id'
      print subcategory_id
      
      with session_scope() as db:
        query = db.query(Business)
        my_or = or_(Business.email==email, Business.name==name, Business.telephone==telephone)
        query = query.filter(my_or)
        biz = query.first()
        if biz is not None:
          print '================ Register biz: email_name_telephone_already_registered'
          print biz.id
          print biz.name
          print biz.account
          return jsonify({'error': 'email_name_telephone_already_registered'})
        
        q2 = db.query(Category).filter(Category.id==category_id).filter(Category.parent_id==None)
        cat = q2.first()
        if cat is None:
          return jsonify({'error': 'category_not_found'})
        
        q3 = db.query(Category).filter(Category.id==subcategory_id).filter(Category.parent_id==category_id)
        subcat = q3.first()
        if subcat is None:
          return jsonify({'error': 'subcategory_not_found'})
        
      rop = register_account_op(
        DISCOIN_ADMIN_ID, 
        DISCOIN_ADMIN_ID, 
        10000, 
        account_name, 
        {
          'weight_threshold' : 1,
          'account_auths'    : [[DISCOIN_ADMIN_ID,1]],
          'key_auths'        : [[owner,1]], 
          'address_auths'    : []
        },
        {
          'weight_threshold' : 1,
          'account_auths'    : [],
          'key_auths'        : [[active,1]], 
          'address_auths'    : []
        },
        memo, 
        DISCOIN_ADMIN_ID,
      )
      rop[1]['fee'] = rpc.db_get_required_fees([rop], '1.3.0')[0]
      
      ref_block_num, ref_block_prefix = ref_block(rpc.db_get_dynamic_global_properties()['head_block_id'])

      tx = build_tx([rop], ref_block_num, ref_block_prefix)

      to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)

      wif = REGISTER_PRIVKEY
      signature = bts2helper_sign_compact(to_sign, wif)

      tx['signatures'] = [signature]

      p = rpc.network_broadcast_transaction_sync(tx)
      print json.dumps(p, indent=2)

      biz = Business()
      with session_scope() as db:
        biz.email           = email
        biz.name            = name
        biz.telephone       = telephone
        biz.account         = account_name
        biz.description     = name
        biz.discount        = Decimal(10)
        biz.category_id     = category_id
        biz.subcategory_id  = subcategory_id
#         _id = cache.get_account_id( unicode(account_name) )
#         biz.account_id  = str(_id if _id else '')
        biz.account_id      = tx["trx"]["operation_results"][0][1] 
        db.add(biz)
        db.commit()
        
#       return jsonify({'tx' : tx})
      return jsonify({'ok':'ok', 'res':p})

    except Exception as e:
      logging.error(traceback.format_exc())
      return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)
    
  @app.errorhandler(404)
  def not_found(error):
    return make_response(jsonify({'error': 'not_found'}), 404)
  
  app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
