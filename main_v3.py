#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

from bitsharesbase.account import BrainKey, Address, PublicKey, PrivateKey
from bitsharesbase.memo import (
      get_shared_secret,
      _pad,
      _unpad,
      encode_memo,
      decode_memo
    )
  
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
          '1.2.26'       : '5JqmMaoHucyZPNQjBdwyVPd5vmvECD57cbZU4zNY9KMcFULDUrH',
  
          'discoin.biz4.subaccount1' : '5JoV4FJuL1cTC81kcaD8aDyRfhzT63uhvnWgYGvfeZggAT2KFDy',
          '1.2.27'                   : '5JoV4FJuL1cTC81kcaD8aDyRfhzT63uhvnWgYGvfeZggAT2KFDy',
  
          'discoin.biz4.subaccount2' : '5J72AuQVrsPgSqrgLhBJFG5ic46pFSnWWB5hj8cNgKwnfqrvnBd',
          '1.2.28'                   : '5J72AuQVrsPgSqrgLhBJFG5ic46pFSnWWB5hj8cNgKwnfqrvnBd',
          
          'discoin.biz4.subaccount3' : '5KD2B1U3bv7nXqD1Bs1pe8EVuhJXnbgDZTxr9aTW9hgQSjqaR8G',
          '1.2.29'                   : '5KD2B1U3bv7nXqD1Bs1pe8EVuhJXnbgDZTxr9aTW9hgQSjqaR8G',
  
          'discoin.biz5'             : '5KD8g6ZFLonwYahnLDU5m7HFiMHZb6f243mC4X3sZjSuC5PZM2R',
          '1.2.30'                   : '5KD8g6ZFLonwYahnLDU5m7HFiMHZb6f243mC4X3sZjSuC5PZM2R',
          
          'discoin.biz6'  : '5HtE1vGyBGSpTn4bwgxjypg5XbQEZsGpULUR9sbVH6PU32NxYL4',
          '1.2.31' 			  : '5HtE1vGyBGSpTn4bwgxjypg5XbQEZsGpULUR9sbVH6PU32NxYL4',

          'discoin.biz7'  : '5K8p5cSgGS5hZjZQqxpLMS4kcB6dCKcVU2hRVEfnWgRYHSUz2bn',
          '1.2.32' 			  : '5K8p5cSgGS5hZjZQqxpLMS4kcB6dCKcVU2hRVEfnWgRYHSUz2bn',

          'discoin.biz8' 	: '5JDTLHWMZZNv4fYdzSkMpRcXdxWTBEJqSQwg18bo4evh8gwhrhg',
          '1.2.33' 			  : '5JDTLHWMZZNv4fYdzSkMpRcXdxWTBEJqSQwg18bo4evh8gwhrhg'
  
       }


def create_app(**kwargs):
  app = Flask(__name__)
  app.debug = True
  app.add_url_rule('/graphql/v3', view_func=GraphQLView.as_view('graphql', schema=theSchema, **kwargs))

  @app.before_request
  def log_request():
    print( request.data)
  
  @app.before_request
  def before_request():
    g.start = time.time()
  
  @app.teardown_request
  def teardown_request(exception=None):
    diff = time.time() - g.start
    print( '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    print ('EL REQUEST TOTAL TOMO =>', diff)
    print ('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    
  CORS(app)
    
  return app

if __name__ == '__main__':
  app = create_app(executor=GeventExecutor(), graphiql=True)
  
  @app.errorhandler(Exception)
  def unhandled_exception(e):
    print( 'ERROR OCCURRED:')
    print( str(e))
    print( traceback.format_exc())
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
      # curl -H "Content-Type: application/json" -X POST -d '{ "configuration": {  "warnings": {    "first": {      "amount" : 66,      "description" : "Limit",      "color": "#FFFF00",      "extra_percentage" : 5    },    "second": {      "amount": 80,      "description" : "",      "color": "#FF0000",      "extra_percentage" : 10    }  },  "boostrap":{    "referral":{      "reward"        : 25,      "max_referrals" : 10,      "max_supply"    : 0    },    "airdrop":{      "max_registered_users" : 10000,      "amount"               : 100,      "max_supply"           : 1000000    },    "transactions":{      "max_refund_by_tx" : 500,      "min_refund_by_tx" : 50,      "max_supply"       : 5000000    },    "refund":[      {        "from_tx" : 0,        "to_tx" : 10000,        "tx_amount_percent_refunded" : 25      },      {        "from_tx" : 10000,        "to_tx" : 50000,        "tx_amount_percent_refunded" : 15      },      {        "from_tx" : 50000,        "to_tx" : 100000,        "tx_amount_percent_refunded" : 10      }    ]  },  "issuing" : {    "new_member_percent_pool" : 10  }} }' http://35.163.59.126:8080/api/v3/dashboard/configuration
      # ToDo: chequear antes de guardar configuration.
      with session_scope() as db:
        nm, is_new = get_or_create(db, NameValue, name  = 'configuration')
        nm.value = request.json.get('configuration')
        nm.updated_at = datetime.utcnow()
        db.add(nm)
        db.commit()
      return jsonify( {'ok':'ok'} );
  
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
    
  @app.route('/api/v3/dashboard/business/list/<skip>/<count>', methods=['GET'])
  def dashboard_business(skip, count):
#     init_model.init_categories()
#     init_model.init_businesses()
#     init_model.init_discount_schedule()
    
    # TODO: procesar cada comercio, y listar tambien montos refunded(out) y discounted (in), historicos
    with session_scope() as db:
      return jsonify( { 'businesses': [ build_business(x) for x in db.query(Business).all()] } );
  
  def build_business(biz):
    business                              = biz.to_dict()
    business['balances']                  = get_business_balances(biz.account_id)
    business['rating']                    = get_business_rate(biz.account_id)
    business['avg_discount_by_category']  = get_avg_discount_by_category(biz.category_id, biz.subcategory_id)
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
    print( '================================== get_business_balances #3')
    return x
  
  def get_business_rate(account_id):
    # ToDo: calculate rates (tenerlo en BBDD) -> Hacer sistema de rating
    return {
      'rating'  : 0,
      'reviews' : {
        'total'   : 0,
        'rate_1'  : 0,
        'rate_2'  : 0,
        'rate_3'  : 0,
        'rate_4'  : 0,
        'rate_5'  : 0
      }
    }
  def get_avg_discount_by_category(cat, subcat):
    # ToDo: calculate avg (tenerlo en BBDD)
    return { 'category': 
              {'category' : cat, 
               'avg_discount' : 25},
            'subcategory': 
              {'subcategory' : subcat, 
               'avg_discount' : 32}
           }
  
  @app.route('/api/v3/dashboard/business/profile/<account_id>/load', methods=['GET'])
  def dashboard_business_profile(account_id):
    with session_scope() as db:
      biz = db.query(Business).filter(Business.account_id==account_id).first()
      return jsonify( { 'business': build_business( biz ) } )
#       return jsonify( { 'business': [ build_business(x) for x in db.query(Business).all()] } );
  
  
  @app.route('/api/v3/dashboard/business/profile/<account_id>/update', methods=['GET', 'POST'])
  def dashboard_update_business_profile(account_id):
    # curl -H "Content-Type: application/json" -X POST -d '{  "business": {    "address": null,    "category_id": 1,    "description": "Larsen",    "discount_schedule": [{  "id"        : 1,  "date"      : "monday",  "discount"  : 30},{  "id"        : 1,  "date"      : "tuesday",  "discount"  : 20}],    "image": null,    "latitude": null,    "location": null,    "longitude": null,    "name": "Larsen",    "subcategory_id": 2  },  "secret": "secrettext_1.2.26"}' http://35.163.59.126:8080/api/v3/dashboard/business/profile/1.2.26/update
    # curl -H "Content-Type: application/json" -X POST -d '{  "business": {    "address": null,    "category_id": 1,    "description": "Larsen",    "discount_schedule": [{  "id"        : 1,  "date"      : "monday",  "discount"  : 30},{  "id"        : 1,  "date"      : "tuesday",  "discount"  : 20}],    "image": null,    "latitude": -22.36,    "location": null,    "longitude": -33.36,    "name": "Larsen",    "subcategory_id": 2  },  "secret": "secrettext_1.2.26"}' http://35.163.59.126:8080/api/v3/dashboard/business/profile/1.2.26/update
    secret_text = 'secrettext_'
    if request.method=='GET':
      the_secret_text = secret_text + account_id
      with session_scope() as db:
        return jsonify( { 'business': db.query(Business).filter(Business.account_id==account_id).first().to_dict_for_update(), 'secret' : the_secret_text } );
      
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

  @app.route('/api/v3/dashboard/business/schedule/<account_id>/update', methods=['GET', 'POST'])
  def dashboard_update_business_schedule(account_id):
    # curl -H "Content-Type: application/json" -X POST -d '{  "business": {    "address": null,    "category_id": 1,    "description": "Larsen",    "discount_schedule": [{  "id"        : 1,  "date"      : "monday",  "discount"  : 30},{  "id"        : 1,  "date"      : "tuesday",  "discount"  : 20}],    "image": null,    "latitude": null,    "location": null,    "longitude": null,    "name": "Larsen",    "subcategory_id": 2  },  "secret": "secrettext_1.2.26"}' http://35.163.59.126:8080/api/v3/dashboard/business/profile/1.2.26/update
    # curl -H "Content-Type: application/json" -X POST -d '{  "business": {    "address": null,    "category_id": 1,    "description": "Larsen",    "discount_schedule": [{  "id"        : 1,  "date"      : "monday",  "discount"  : 30},{  "id"        : 1,  "date"      : "tuesday",  "discount"  : 20}],    "image": null,    "latitude": -22.36,    "location": null,    "longitude": -33.36,    "name": "Larsen",    "subcategory_id": 2  },  "secret": "secrettext_1.2.26"}' http://35.163.59.126:8080/api/v3/dashboard/business/profile/1.2.26/update
    secret_text = 'secrettext_'
    if request.method=='GET':
      the_secret_text = secret_text + account_id
      with session_scope() as db:
        biz = db.query(Business).filter(Business.account_id==account_id).first()
        if not biz:
          return jsonify( { 'error' : 'account_id_not_found'} )
        return jsonify( { 'discount_schedule' : [x.to_dict() for x in biz.discount_schedule] if biz.discount_schedule else [] , 'secret' : the_secret_text } );
          
    biz_schedule_json  = request.json.get('discount_schedule', [])
    signed_secret      = request.json.get('signed_secret')
    
    # ToDo: obtener minimo descuento de categoria y pasarlo como parametro
    errors = DiscountSchedule.validate_schedule(biz_schedule_json, 20)
    if len(errors)>0:
      return jsonify(errors)
    with session_scope() as db:
      biz = db.query(Business).filter(Business.account_id==account_id).first()
      if not biz:
        return jsonify( { 'error' : 'account_id_not_found'} )
      biz.discount_schedule[:] = []
      db.add(biz)
      for schedule in biz_schedule_json:
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
  
  def whatisthis(s):
    if isinstance(s, str):
        print (s, " is a ordinary string")
    elif isinstance(s, unicode):
        print (s, " is a unicode string")
    else:
        print ("not a string")
  
  # Login
  @app.route('/api/v3/business/login/', methods=['GET', 'POST'])
  def business_login():
    import codecs
    import unicodedata
    pubKey        = rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['options']['memo_key']
    memo_from     = str(request.json.get('from'))
    memo_to       = str(request.json.get('to'))
    memo_nonce    = 0
    memo_message  = str(request.json.get('message'))
    print( pubKey)
    print( memo_from,  memo_to, memo_nonce, memo_message)
#     whatisthis(memo_message)
    
#     memo_message = '7505b97933b143eadddfda7ba2f92c14'.encode().decode('utf-8')
#     memo_message = '%s' % unicodedata.normalize('NFKD', memo_message).encode('ascii','ignore')
    memo_message = u'%s' % memo_message
    print(memo_message, ' --> tocado')
    dec = decode_memo(  PrivateKey(REGISTER_PRIVKEY),
                        PublicKey(memo_from, prefix='BTS'),
                        0,
                        memo_message)

    #msg   = bts2helper_memo_encode(REGISTER_PRIVKEY, str(memo_from), str('123456789').encode('hex'))
    #msg   = bts2helper_memo_decode(REGISTER_PRIVKEY, pubKey, memo_from, memo_to, memo_nonce, memo_message)
    
    return jsonify( { 'res' : str(dec) } )
  
  # Lista las subcuentas de un business.
  @app.route('/api/v3/business/<business_id>/subaccount/list/<start>', methods=['GET', 'POST'])
  def business_account_list(business_id, start):
    # EJEMPLO: http://35.163.59.126:8080/api/v3/business/1.2.25/subaccount/list/0
    print( ' == get_withdraw_permissions_by_giver:')
    if not start or str(start).strip()=='0':
      start = '1.12.0'
    perms = rpc.db_get_withdraw_permissions_by_giver(business_id, start, 100)
    subaccounts = []
    for perm in perms:
      # Check if account already added???
      subaccounts.append( build_subaccount ( cache.get_account(perm['authorized_account']), perm ) )
    return jsonify( { 'subaccounts': subaccounts, 'permissions' : perms} )

  def build_subaccount(account, perm):
    asset = rpc.db_get_assets([DISCOIN_ID])[0]
    return { 
      'name'        : account['name'],  
      'id'          : account['id'],
      'amount'      : amount_value(perm['withdrawal_limit']['amount'], asset), 
      'expiration'  : perm['expiration'],  
      'since'       : perm['period_start_time'],
      'interval'    : perm['withdrawal_period_sec']
    }
    
  # Lista los business que lo hicieron subcuenta al account_id.
  @app.route('/api/v3/business/subaccount/list/<account_id>', methods=['GET', 'POST'])
  def business_account_list_permissions(account_id):
    # EJEMPLO: http://35.163.59.126:8080/api/v3/business/subaccount/list/1.2.27
    res = rpc.db_get_withdraw_permissions_by_recipient(account_id, '1.12.0', 100)
    print( json.dumps(res, indent=2))
    return jsonify( { 'subaccounts' : res } )
  
  # Crea la TX para agregar una subcuenta a un negocio, habilita a una cuenta a "chupar" de la cuenta madre del negocio.
  @app.route('/api/v3/business/subaccount/add_or_update/create', methods=['POST'])
  def subaccount_add_or_update_create():
    # EJEMPLO: curl -H "Content-Type: application/json" -X POST -d '{"business_id" : "1.2.25", "subaccount_id" : "1.2.27", "limit" : "2000", "_from" : null, "period" : null, "periods" : 365}' http://35.163.59.126:8080/api/v3/business/subaccount/add_or_update/create  
    business_id     = request.json.get('business_id')
    subaccount_id   = request.json.get('subaccount_id')  
    limit           = request.json.get('limit')
    _from           = request.json.get('from')
    period          = request.json.get('period')
    periods         = request.json.get('periods')
  
    tx = subaccount_add_or_update_create_impl(business_id, subaccount_id, limit, _from, period, periods)
    
    if 'error' in tx:
      return jsonify(tx)
    
    return jsonify( {'tx':tx} )
  
  def subaccount_add_or_update_create_impl(business_id, subaccount_id, limit, _from, period, periods):
    
    print( ' == subaccount_add_or_update_create_impl #1')
    # Check if business has credit.
    p = rpc.db_get_account_balances(business_id, [DISCOIN_CREDIT_ID])
    if p[0]['amount'] <= 0:
      return {'error':'business_has_no_credit'}
    # Check if subaccount is valid account.
    print( ' == subaccount_add_or_update_create_impl #2')
    subaccounts = rpc.db_get_accounts([subaccount_id])
    if not subaccounts or len(subaccounts)==0:
      return {'error': 'subaccount_not_exists'}
    
    print( ' == subaccount_add_or_update_create_impl #2')
    # Validamos que la subaccount_id no tenga ya permisos de withdraw por parte del comercio:
    perm = get_withdraw_permission(business_id, subaccount_id)
#     if perm:
#       return {'error': 'subaccount_id_already_has_permission'}
      
    print( ' ======================================================')
    print (' ====== subaccount_add_or_update_create_impl #3')
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
    
    print( ' ======================================================')
    print (' ====== subaccount_add_or_update_create_impl #4')
    my_amount = reverse_amount_value(limit, asset)
    my_amount_asset = {
      'amount'  : int(my_amount),
      'asset_id'   : DISCOIN_ID
    }
    if perm:
      print( ' == IS UPDATE')
#       print json.dumps(perm, indent=2)
      withdraw_permission_op = withdraw_permission_update(business_id, subaccount_id, my_amount_asset, period, periods, _from, perm, None, CORE_ASSET)
    else:
      print (' == IS CREATE')
      withdraw_permission_op = withdraw_permission_create(business_id, subaccount_id, my_amount_asset, period, periods, _from, None, CORE_ASSET)
    
    
    fees = rpc.db_get_required_fees([withdraw_permission_op[0]] , CORE_ASSET)
    
    print( ' == fees: ')
    print (fees)
    print (' == Calc fee')
    print (amount_value(fees[0]['amount'], asset_core))
    
    _transfer = transfer(
        DISCOIN_ADMIN_ID,
        business_id,
        asset_core,
        amount_value(fees[0]['amount'], asset_core),
        '',
        None,
        CORE_ASSET
    )
    print( ' == transfer: ')
    print (_transfer)
    
    
#     _transfer +
    tx = build_tx_and_broadcast(
      [_transfer[0]] + [withdraw_permission_op[0]] 
    , None)
    
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    tx['signatures'] = [signature]
    return tx
  
  # Broadcastea la TX para agregar una subcuenta a un negocio, habilita a una cuenta a "chupar" de la cuenta madre del negocio.
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

    tx = subaccount_add_or_update_create_impl(business_id, subaccount_id, limit, _from, period, periods)
    
    if 'error' in tx:
      return jsonify(tx)
    
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    
    signature = bts2helper_sign_compact(to_sign, wifs[business_id])
    
    if 'signatures' not in tx: 
      tx['signatures'] = []
    tx['signatures'].append(signature);    
    
    # como listamos los permisos? -> get_account_history_by_operations discoin.biz3 [25] 0 100 ??
    # como testeamos el permiso?  -> transfer discoin.biz4.subaccount1 discoin.biz4.subaccount2 10000 THEDISCOIN.M "ehhh" true

    res = rpc.network_broadcast_transaction_sync(tx)
    print( json.dumps(res, indent=2))
    return jsonify( {'res':res} )
  
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # Subaccount Refund (aka claim) Management
  # =================================================================================================
  
  # Crea la TX para refundear una compra.
  @app.route('/api/v3/business/subaccount/refund/create', methods=['POST'])
  def subaccount_refund_create():
    # curl -H "Content-Type: application/json" -X POST -d '{"business_id" : "1.2.25", "subaccount_id" : "1.2.27", "to" : "1.2.19", "amount" : 500, "bill_amount" : 2000, "bill_id" : "this_is_a_bill_id"}' http://35.163.59.126:8080/api/v3/business/subaccount/refund/create  
    business_id     = request.json.get('business_id')
    subaccount_id   = request.json.get('subaccount_id')
    _to             = request.json.get('to')  
    amount          = request.json.get('amount')  
    bill_amount     = request.json.get('bill_amount')  
    bill_id         = request.json.get('bill_id')  

    tx = subaccount_refund_impl(business_id, subaccount_id, _to, amount, bill_amount, bill_id)
    
    return jsonify( {'tx':tx} )
  
  # Retorna los permisos de "retiro" que tiene una cuenta en un negocio.
  def get_withdraw_permission(business_id, subaccount_id):
    
    print( ' == get_withdraw_permission #1')
    res = rpc.db_get_withdraw_permissions_by_recipient(subaccount_id, '1.12.0', 100)
    for p in res[::-1]:
#       print ' == get_withdraw_permission #2'
#       print json.dumps(p, indent=2)
      if p['withdraw_from_account'] == business_id and p['withdrawal_limit']['asset_id'] == DISCOIN_ID:
        return p['id']
    return None
    
  def subaccount_refund_impl(business_id, subaccount_id, _to, amount, bill_amount, bill_id):
    
    print( ' === subaccount_refund_impl #1')
    asset, asset_core = rpc.db_get_assets([DISCOIN_ID, CORE_ASSET])
    
    print (' === subaccount_refund_impl #2')
    my_amount = reverse_amount_value(amount, asset)
    my_amount_asset = {
      'amount'   : int(my_amount),
      'asset_id' : DISCOIN_ID
    }
    
    print( ' === subaccount_refund_impl #3')
    withdraw_permission          = get_withdraw_permission(business_id, subaccount_id)
    
    print (' === subaccount_refund_impl #4')
    if not withdraw_permission:
      return {'error': 'subaccount_has_no_permission'}
    
    print( withdraw_permission)
    print (' === subaccount_refund_impl #5')
    withdraw_permission_claim_op = withdraw_permission_claim(withdraw_permission, business_id, subaccount_id, my_amount_asset, None, CORE_ASSET)
    
    print (' == withdraw_permission_claim_op: ')
    print (withdraw_permission_claim_op)
    
    
    _refund = transfer(
        subaccount_id,
        _to,
        asset,
        amount
    )
    print( ' == refund: ')
    print (_refund)
    
    fees = rpc.db_get_required_fees([withdraw_permission_claim_op[0], _refund] , CORE_ASSET)
    
    print (' == fees: ')
    print (fees)
    
    _transfer = transfer(
        DISCOIN_ADMIN_ID,
        subaccount_id,
        asset_core,
        amount_value(fees[0]['amount'], asset_core)+amount_value(fees[1]['amount'], asset_core)
      )
    print (' == transfer: ')
    print (_transfer)
    
    tx = build_tx_and_broadcast(
      _transfer + [withdraw_permission_claim_op[0]] + _refund
    , None)
    
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    tx['signatures'] = [signature]
    return tx

  # Broadcastea la TX para refundear una compra.
  @app.route('/api/v3/business/subaccount/refund/create/broadcast', methods=['POST'])
  def subaccount_refund_and_broadcast():
    
    # curl -H "Content-Type: application/json" -X POST -d '{"business_id" : "1.2.25", "subaccount_id" : "1.2.27", "to" : "1.2.19", "amount" : 500, "bill_amount" : 2000, "bill_id" : "this_is_a_bill_id"}' http://35.163.59.126:8080/api/v3/business/subaccount/refund/create/broadcast  
    business_id     = request.json.get('business_id')
    subaccount_id   = request.json.get('subaccount_id')
    _to             = request.json.get('to')  
    amount          = request.json.get('amount')  
    bill_amount     = request.json.get('bill_amount')  
    bill_id         = request.json.get('bill_id')  

    tx = subaccount_refund_impl(business_id, subaccount_id, _to, amount, bill_amount, bill_id)
    
    if 'error' in tx:
      return jsonify( tx )
    
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    
    signature = bts2helper_sign_compact(to_sign, wifs[subaccount_id])
    
    if 'signatures' not in tx: 
      tx['signatures'] = []
    tx['signatures'].append(signature);    
    
    res = rpc.network_broadcast_transaction_sync(tx)
    print( json.dumps(res, indent=2))
    return jsonify( {'res':res, 'tx':tx} )
  
    
  @app.route('/api/v3/account/change_keys/<account>/<owner>/<active>/<memo_key>', methods=['GET'])
  def change_keys(account, owner, active, memo_key):
    from credit_func import account_id
    
    accounts = { a[0]:a[1] for a in rpc.db_get_full_accounts(list(set(account)), False) }
    assets = { a['symbol']:a for a in rpc.db_get_assets(['1.3.0']+[DISCOIN_ID]) }
    assets_by_id = { assets[k]['id']:assets[k] for k in assets }
    
    active_auth = {
      'weight_threshold' : 1,
      'account_auths'    : [],
      'key_auths'        : [[active,1]], 
      'address_auths'    : []
    }

    owner_auth = {
      'weight_threshold' : 1,
      'account_auths'    : [[DISCOIN_ADMIN_ID,1]],
      'key_auths'        : [[owner,1]], 
      'address_auths'    : []
    }

    au_op = account_update_op(
      account_id(account), 
      owner_auth, 
      active_auth, 
      {'memo_key':memo_key}
    )
    
    tx = build_tx_and_broadcast(
      [au_op] 
    , None)
    return jsonify( {'tx':tx} )

  # Crea la TX para invitar a una negocio a que claimee su credito.
  @app.route('/api/v3/business/endorse/create', methods=['POST'])
  def endorse_create():
    # TEST: curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz1","initial_credit":"10000"}' http://35.163.59.126:8080/api/v3/business/endorse/create
    
    business_name   = request.json.get('business_name')  
    initial_credit  = request.json.get('initial_credit')

    tx = endorse_create_impl(business_name, initial_credit)
    
    if 'error' in tx:
      return jsonify( tx )
    return jsonify( {'tx':tx} )
  
  def endorse_create_impl(business_name, initial_credit):
    
    business_id     = cache.get_account_id(business_name)
    
    print( ' ======================================================')
    print (' ====== XX endorse_create_impl #1')
    # TODO: utilizar el sender(to) en vez de DISCOIN_ADMIN_ID.
    # Check if admin account has access tokens.
    p = rpc.db_get_account_balances(DISCOIN_ADMIN_ID, [DISCOIN_ACCESS_ID])
    if p[0]['amount'] == 0:
      return {'error':'no_endorsement_available'}
    
    print( ' ======================================================')
    print (' ====== XX endorse_create_impl #2')
    # Check if business has credit.
    p = rpc.db_get_account_balances(business_id, [DISCOIN_CREDIT_ID])
    if p[0]['amount'] > 0:
      return {'error':'already_have_credit'}
    
    print( ' ======================================================')
    print (' ====== XX endorse_create_impl #3')
    p = rpc.db_get_account_balances(business_id, [DISCOIN_ACCESS_ID])
    if p[0]['amount'] > 0:
      return {'error':'already_have_endorsement'}

    print( ' ======================================================')
    print( ' ====== XX endorse_create_impl #4')
    asset, asset_core = rpc.db_get_assets([DISCOIN_ACCESS_ID, CORE_ASSET])
    
    # ~ie:<%y%m%d>:<1.2.1526>:25000
    utc_now = datetime.utcnow().strftime('%y%m%d')
    memo = {
      'message' : '~ie:{0}:{1}:{2}'.format(utc_now, business_id, initial_credit).encode('hex')
    }
    
#       'from'    : 'GPH6bM4zBP7PKcSmXV7voEdauT6khCDGUqXyAsq5NCHcyYaNSMYBk',
#       'to'      : 'GPH6bM4zBP7PKcSmXV7voEdauT6khCDGUqXyAsq5NCHcyYaNSMYBk',
#       'nonce'   : 123456
        
    print( ' ======================================================')
    print( ' ====== XX endorse_create_impl #5')
   
    endorse_transfer_op = transfer(DISCOIN_ADMIN_ID, business_id, asset, initial_credit, memo, None, CORE_ASSET)
    
    # Para ver prototipos de TXs ver http://docs.bitshares.org/bitshares/tutorials/construct-transaction.html 

    print( ' ======================================================')
    print( ' ====== XX endorse_create_impl #6')
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
    
    print( ' ======================================================')
    print (' ====== XX endorse_create_impl #7')
    print (' ======================================================')
    
    return tx
  
  # Broadcastea la TX para invitar a una negocio a que claimee su credito.
  @app.route('/api/v3/business/endorse/create/broadcast', methods=['POST'])
  def endorse_create_and_broadcast():
    # TEST: curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz3","initial_credit":"12500"}' http://35.163.59.126:8080/api/v3/business/endorse/create/broadcast
    business_name   = request.json.get('business_name')  
    initial_credit  = request.json.get('initial_credit')  
    print( ' ======================================================')
    print (' ====== endorse_create_and_broadcast #1')
    tx  = endorse_create_impl(business_name, initial_credit)
    
    print (' ======================================================')
    print (' ====== endorse_create_and_broadcast #2')
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    
    print( ' ======================================================')
    print( ' ====== endorse_create_and_broadcast #3')
    signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    tx['signatures'] = [signature]
    
    
    res = rpc.network_broadcast_transaction_sync(tx)
    print( json.dumps(res, indent=2))
    
    return jsonify( {'res':res, 'tx':tx} )
  
  # Crea la TX para que un negocio accceda a su credito.
  @app.route('/api/v3/business/endorse/apply', methods=['POST'])
  def endorse_apply():
    
    business_name   = request.json.get('business_name')  
#     initial_credit  = request.json.get('initial_credit')

    tx = endorse_apply_impl(business_name)
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
    
    print( ' ==== ACCESS BALANCE:')
    print( access_balance[0]['amount'])
    
    apply_transfer_op = transfer(
      business_id,
      DISCOIN_ADMIN_ID,
      asset,
      access_balance[0]['amount'],
      memo,
      None,
      CORE_ASSET
    )[0]

    print( "************************************************")
    print( json.dumps(apply_transfer_op, indent=2))
    print( "*********************")

    # fees = rpc.db_get_required_fees([endorse_transfer_op], CORE_ASSET)
    print( "toma => ", apply_transfer_op[1]['fee']['amount'])
    print( "************************************************")

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
  
  # Broadcastea la TX para que el negocio accceda a su credito.
  @app.route('/api/v3/business/endorse/apply/broadcast', methods=['POST'])
  def endorse_apply_and_broadcast():
    # TEST: 
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz1","initial_credit":"10000"}' http://35.163.59.126:8080/api/v3/business/endorse/apply/broadcast
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz2","initial_credit":"15000"}' http://35.163.59.126:8080/api/v3/business/endorse/apply/broadcast
    # curl -H "Content-Type: application/json" -X POST -d '{"business_name":"discoin.biz3"}' http://35.163.59.126:8080/api/v3/business/endorse/apply/broadcast
    business_name   = request.json.get('business_name')  
#     initial_credit  = request.json.get('initial_credit')
    
#     op_id           = request.json.get('op_id')
    print( ' ======================================================')
    print( ' ====== endorse_apply_and_broadcast #1')
    
#     tx  = endorse_apply_impl(business_name, initial_credit)
    tx  = endorse_apply_impl(business_name)
    
    print( ' ======================================================')
    print( ' ====== endorse_apply_and_broadcast #2')
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    
    print( ' ======================================================')
    print( ' ====== endorse_apply_and_broadcast #3')
    signature = bts2helper_sign_compact(to_sign, wifs[business_name])
    
    if 'signatures' not in tx: 
      tx['signatures'] = []
    tx['signatures'].append(signature);
    
    res = rpc.network_broadcast_transaction_sync(tx)
    print( json.dumps(res, indent=2))
    return jsonify( {'res':res, 'tx':tx} )
  
  
  # Crea la TX para que un negocio accceda a su credito.
  @app.route('/api/v3/business/<business_name>/overdraft/modify', methods=['POST'])
  def modify_overdraft(business_name):
    
    new_overdraft  = request.json.get('new_overdraft')
    # ToDo: Chequear valores, si tiene overdraft o no, etc.
    
    obj = {
      business_name  : new_overdraft
    }

    return jsonify( {'ok':'ok'} )
    
    print( "apply auth => about to apply overdraft")
    set_overdraft(obj)

    return jsonify( {'ok':'ok'} )
  
  
  
  
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
    print( ' ============== about to query categories')
    with session_scope() as db:
      q2 = db.query(Category)
      if len(search)>0:
        my_search = '%'+search+'%'
        print( ' ============== search:')
        print( search)
        print( my_search)
        my_or = or_(Category.name.like(my_search), Category.description.like(my_search))
        q2 = q2.filter(my_or)
      if cat_level==1:
        q2 = q2.filter(Category.parent_id==None)
      if cat_level==0:
        q2 = q2.filter(Category.parent_id==None)
      if cat_level>0:
        q2 = q2.filter(Category.parent_id==cat_level)
      q2.order_by(Category.name).order_by(Category.description)
      print( ' ============== cat_level:')
      print( cat_level)
      data = [ {'id' : c.id, 'name': c.name, 'description': c.description, 'parent_id': c.parent_id} for c in q2.all()] 
      print (' ============== query result:')
      print (json.dumps(data))
      print (' ============== END!')
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
    print( json.dumps(res, indent=2))
    return jsonify( {'res':res} )
  
  @app.route('/api/v3/sign_and_push_tx', methods=['POST'])
  def sign_and_push_tx():
    tx  = request.json.get('tx')
    pk  = request.json.get('pk')
    
    priv_key = str(pk)
    
    print (' ===> TX:')
    print (json.dumps(tx, indent=2))
    print (' ===> pk:')
    print (pk)
    
    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    print (' ===> TO-SIGN:')
    print (to_sign)
    signature = bts2helper_sign_compact(to_sign, priv_key)
    print ('=== PRE ADD SIGNATURE:')
    
    if 'signatures' not in tx: 
      tx['signatures'] = []
    tx['signatures'].append(signature);    
    
    print (' ===> SIGNED TX:')
    print (json.dumps(tx, indent=2))
    
    res = rpc.network_broadcast_transaction_sync(tx)
    print (json.dumps(res, indent=2))
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
    
    print( ' ========================== Find Account by PubKey')
    key  = request.json.get('key')
    account_ids = set(rpc.db_get_key_references([key])[0])
    print (' == account_ids : ')
    print (account_ids)
    res = [real_name(a['name']) for a in rpc.db_get_accounts(list(account_ids))]
    print (' == res : ')
    print (json.dumps(res) )
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
          print( '=== Account: ')
          print (tmp[0])
          # Only with no-credit and no black-listed
          if search_filter == 1:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
            print( '=== Overdraft: ')
            print (p[0]['amount'])
            no_credit = p[0]['amount'] == 0
            no_black = tmp[1] not in rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['blacklisted_accounts']
            add_account = no_credit and no_black
          
          # Only with credit
          if search_filter == 2:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
            has_credit = p[0]['amount'] > 0
            #no_black = tmp[1] not in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']
            add_account = has_credit
          print ('===============')
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
      print( json.dumps(p, indent=2))
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
      
      print ('================== category_id')
      print (category_id)
      print ('================== subcategory_id')
      print (subcategory_id)
      
      with session_scope() as db:
        query = db.query(Business)
        my_or = or_(Business.email==email, Business.name==name, Business.telephone==telephone)
        query = query.filter(my_or)
        biz = query.first()
        if biz is not None:
          print ('================ Register biz: email_name_telephone_already_registered')
          print (biz.id)
          print (biz.name)
          print (biz.account)
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
      print( json.dumps(p, indent=2))

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
  
  app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT",8089)))
