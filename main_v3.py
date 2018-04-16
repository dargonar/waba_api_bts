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
      return jsonify( {'method':request.method} );
    
  @app.route('/api/v3/dashboard/business/<with_balance>/<skip>/<count>', methods=['GET'])
  def dashboard_business(with_balance, skip, count):
#     init_model.init_categories()
#     init_model.init_businesses()
#     init_model.init_discount_schedule()
    
    # TODO: procesar cada comercio, y listar tambien montos refunded(out) y discounted (in), historicos
    with session_scope() as db:
#       return jsonify( { 'businesses': [ x.to_dict(str2bool(with_balance)) for x in db.query(Business).all()] } );
      return jsonify( { 'businesses': [ x.to_dict(str2bool(with_balance)) for x in db.query(Business).all()] } );
    
  
  @app.route('/api/v3/dashboard/business/<account_id>/profile/<with_balance>', methods=['GET'])
  def dashboard_business_profile(account_id, with_balance):
    with session_scope() as db:
      return jsonify( { 'business': db.query(Business).filter(Business.account_id==account_id).first().to_dict(str2bool(with_balance))} );
  
#   @app.route('/api/v3/overdraft/invite', methods=['POST'])
#   def invite_overdraft():
#     business_name   = request.json.get('business_name')  
#     initial_credit  = request.json.get('initial_credit')    
#     business_id     = cache.get_account_id(business_name)
    
  @app.route('/api/v3/endorse/create', methods=['POST'])
  def endorse_create():
    # TEST: curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz1","initial_credit":"10000"}' http://35.163.59.126:8080/api/v3/endorse/create
    
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

  @app.route('/api/v3/endorse/create/broadcast', methods=['POST'])
  def endorse_create_and_broadcast():
    # TEST: curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz3","initial_credit":"12500"}' http://35.163.59.126:8080/api/v3/endorse/create/broadcast
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
  
  @app.route('/api/v3/endorse/apply', methods=['POST'])
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
  
  @app.route('/api/v3/endorse/apply/broadcast', methods=['POST'])
  def endorse_apply_and_broadcast():
    # TEST: 
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz1","initial_credit":"10000"}' http://35.163.59.126:8080/api/v3/endorse/apply/broadcast
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz2","initial_credit":"15000"}' http://35.163.59.126:8080/api/v3/endorse/apply/broadcast
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz3","initial_credit":"12500"}' http://35.163.59.126:8080/api/v3/endorse/apply/broadcast
    business_name   = request.json.get('business_name')  
    initial_credit  = request.json.get('initial_credit')
    
    wifs = { 'discoin.biz1' : '5J1DdLRTrwxYxFih33A8wgxRLE7hqTz6Te58ES94kqJEBsMuH3B',
             'discoin.biz2' : '5JaAXXB9jMEVSVEyX6DQSskQhqXRr67HwZ1jLPwHyysPWQtuZgR',
             'discoin.biz3' : '5Kjz35R9W3m5ZpznZMSpdySz35tZsXZbzsuSdbtV12YC9Zaxzd9'}
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
  
  @app.route('/api/v3/push_id', methods=['POST'])
  def push_id():
    with session_scope() as db:
      pi, is_new = get_or_create(db, PushInfo,
        name  = request.json.get('name'),
      )
      pi.push_id = request.json.get('push_id')
      pi.updated_at = datetime.utcnow()
      db.add(pi)
      db.commit()
    
    return jsonify( 'ok' )

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

  @app.route('/api/v3/find_account', methods=['POST'])
  def find_account():
    key  = request.json.get('key')
    account_ids = set(rpc.db_get_key_references([key])[0])
    return jsonify([real_name(a['name']) for a in rpc.db_get_accounts(list(account_ids))])

  @app.route('/api/v3/account/<account>', methods=['GET'])
  def get_account(account):

    if str(account) != str('gobierno-par'):
      account = ACCOUNT_PREFIX+account

    return jsonify( rpc.db_get_account_by_name(account) )
  
  @app.route('/api/v3/searchAccount', methods=['GET'])
  def search_account():
    search = request.args.get('search', '')
    search_filter = int(request.args.get('search_filter',0))

    res = []
    for tmp in rpc.db_lookup_accounts(ACCOUNT_PREFIX + search, 10):
      if tmp[0].startswith(ACCOUNT_PREFIX):
        tmp[0] = tmp[0][len(ACCOUNT_PREFIX):]

        #print tmp[0], search
        if tmp[0].startswith(search):
          
          add_account = True

          # Only with no-credit and no black-listed
          if search_filter == 1:
            p = rpc.db_get_account_balances(tmp[1], [DESCUBIERTO_ID])
            no_credit = p[0]['amount'] == 0
            no_black = tmp[1] not in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']
            add_account = no_credit and no_black
          
          # Only with credit
          if search_filter == 2:
            p = rpc.db_get_account_balances(tmp[1], [DESCUBIERTO_ID])
            has_credit = p[0]['amount'] > 0
            #no_black = tmp[1] not in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']
            add_account = has_credit

          if add_account:
            res.append( tmp )

    return jsonify( res )

  @app.route('/api/v3/register', methods=['POST'])
  def register():
    try:
      req = request.json
      name   = ACCOUNT_PREFIX + str( req.get('name') )
      
      if req.get('secret') == 'cdc1ddb0cd999dbc5ba8d7717e3837f5438af8198d48c12722e63a519e73a38c':
        name = str( req.get('name') )
        
      owner  = str( req.get('owner') )
      active = str( req.get('active') )
      memo   = str( req.get('memo') )
      
      if not bts2helper_is_valid_name(name):
        return jsonify({'error': 'is_not_valid_name'})

      if not bts2helper_is_cheap_name(name):
        return jsonify({'error': 'is_not_cheap_name'})

      acc = rpc.db_get_account_by_name(name)
      if acc is not None:
        return jsonify({'error': 'already_taken'})

      rop = register_account_op(
        PROPUESTA_PAR_ID, 
        GOBIERO_PAR_ID, 
        10000, 
        name, 
        {
          'weight_threshold' : 1,
          'account_auths'    : [[GOBIERO_PAR_ID,1]],
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
        GOBIERO_PAR_ID,
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
      return jsonify({'ok':'ok', 'coco':p})

    except Exception as e:
      logging.error(traceback.format_exc())
      return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)
  
  @app.errorhandler(404)
  def not_found(error):
    return make_response(jsonify({'error': 'not_found'}), 404)
  
  app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
