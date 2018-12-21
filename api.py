# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import logging
import traceback
import time

from datetime import datetime, timedelta
from decimal import Decimal

from flask import Flask, jsonify, make_response, request, g
from flask import send_from_directory
from flask_graphql import GraphQLView
from flask_cors import CORS, cross_origin

from schema_v3 import theSchema, templates
from utils import *

from models import *
Base.metadata.create_all(get_engine())

from datatables import ColumnDT, DataTables

from ops import *
from ops_func import *
from bts2helper import *
import simplejson as json
from graphql.execution.executors.gevent import GeventExecutor
from graphql.execution.executors.thread import ThreadExecutor

#ACCOUNT_PREFIX = '' 
from memcache import Client
import rpc
import cache
import cache_db
import init_model

from bitsharesbase.account import BrainKey, Address, PublicKey, PrivateKey
from bitsharesbase.memo import (
      get_shared_secret,
      _pad,
      _unpad,
      encode_memo,
      decode_memo
    )

from jsondiff import diff
import hashlib, binascii

import urllib.parse
import urllib.request

import stats

ERR_UNKNWON_ERROR    = 'unknown_error'

# REGISTER_PRIVKEY     = '5JQGCnJCDyraociQmhDRDxzNFCd8WdcJ4BAj8q1YDZtVpk5NDw9'

mc = Client(['127.0.0.1:11211'], debug=0)

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
#   app = create_app(executor=GeventExecutor(), graphiql=True)
  app = create_app(executor=ThreadExecutor(), graphiql=True)
  
  @app.errorhandler(Exception)
  def unhandled_exception(e):
    print( 'ERROR OCCURRED:')
    print( str(e))
    print( traceback.format_exc())
    return make_response(jsonify({'error': str(e)}), 500)

  @app.route('/status', methods=['POST', 'GET'])
  def status():
    return jsonify({'ok':'ok'})

  @app.route('/api/v3/dashboard/kpis', methods=['POST', 'GET'])
  def dashboard_kpis():
    
#     main_asset = cache.get_asset(DISCOIN_ID)
    main_asset = rpc.db_get_assets([DISCOIN_ID])
    users      = rpc.db_get_asset_holders_count(DISCOIN_ID)
    
    # ToDo: Construir KPIs posta
    supply  = stats.get_asset_supply(DISCOIN_ID, mc)
    airdrop = stats.get_asset_airdrop(DISCOIN_ID, mc)
    _now    = datetime.utcnow()
    balances = get_business_balances(DISCOIN_ADMIN_ID)
    return jsonify( 
        {
          'updated_at':   str(_now),
          'main_asset':   supply,
          'airdrop':      airdrop,
          'balances':     balances,
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
      
      my_config = cache_db.get_configuration()
      
      asset_balance, asset_overdraft, asset_invite = rpc.db_get_assets([DISCOIN_ID, DISCOIN_CREDIT_ID, DISCOIN_ACCESS_ID])
      
      asset_balance['key']    = 'balance'
      asset_overdraft['key']  = 'descubierto' 
      asset_invite['key']     = 'invitado'
      assets                  = {'asset_balance':asset_balance, 'asset_overdraft':asset_overdraft, 'asset_invite':asset_invite}
      print(' --------- my_config[value]:')
      print(my_config['value'])
      return jsonify( { 'configuration': my_config['value'], 'assets' : assets, 'updated_at' : my_config['updated_at'] } )
    
    if request.method=='POST':
      # ToDo: chequear antes de guardar configuration.
      # Validate 
      schema = cache_db.get_configuration() #init_model.get_default_configuration()
      config = request.json.get('configuration')
      if not config or config=={}:
        return jsonify( { 'error': 'configuration_empty'} )
      str_diff = str(diff(schema['value'], config))
      
      print(' --------- config received')
      print(json.dumps(config ))
      print ('------------str_diff', str_diff)
#       return jsonify( {'ok':'ok'} )
    
      
      if 'delete' in str_diff:
        return jsonify( { 'error': 'not_valid_json_structure' , 'error_desc': str_diff} )
      config["warnings"]["first"]["from_amount"]=0
      if try_int(config["warnings"]["first"]["from_amount"])<0:
        return jsonify( { 'error': 'warning_1_must_be_greater_zero'} )
      if try_int(config["warnings"]["second"]["from_amount"])<0:
        return jsonify( { 'error': 'warning_2_must_be_greater_zero'} )
      if try_int(config["warnings"]["third"]["from_amount"])<0:
        return jsonify( { 'error': 'warning_3_must_be_greater_zero'} )
      if try_int(config["warnings"]["first"]["from_amount"])>try_int(config["warnings"]["second"]["from_amount"]):
        return jsonify( { 'error': 'warning_1_not_minor_warning_2'} )
      if try_int(config["warnings"]["second"]["from_amount"]) >= try_int(config["warnings"]["third"]["from_amount"]):
        return jsonify( { 'error': 'warning_2_not_minor_warning_3'} )
      if try_int(config["warnings"]["third"]["from_amount"])>100:
        return jsonify( { 'error': 'warning_3_not_minor_100'} )
      config["warnings"]["first"]["to_amount"] = config["warnings"]["second"]["from_amount"]
      config["warnings"]["second"]["to_amount"] = config["warnings"]["third"]["from_amount"]
      config["warnings"]["third"]["to_amount"] = 100
      if try_int(config["warnings"]["first"]["extra_percentage"]) <0 or try_int(config["warnings"]["first"]["extra_percentage"]) >100:
        return jsonify( { 'error': 'warning_1_extra_perc_between_0_100'} )
      if try_int(config["warnings"]["second"]["extra_percentage"]) <0 or try_int(config["warnings"]["second"]["extra_percentage"]) >100:
        return jsonify( { 'error': 'warning_2_extra_perc_between_0_100'} )
      if try_int(config["warnings"]["third"]["extra_percentage"]) <0 or try_int(config["warnings"]["third"]["extra_percentage"]) >100:
        return jsonify( { 'error': 'warning_3_extra_perc_between_0_100'} )
      
      if try_float(config["reserve_fund"]["new_business_percent"])<0.0 or try_float(config["reserve_fund"]["new_business_percent"])> 100.0:
        return jsonify( { 'error': 'issuing_new_member_percent_pool_must_be_greater_0_and_less_100'} )
      
      config["airdrop"]["by_reimbursement"]["first"]["from_tx"] = 0
      if try_int(config["airdrop"]["by_reimbursement"]["second"]["from_tx"]) < 0:
        return jsonify( { 'error': 'airdrop_reimbursment_2_must_be_greater_zero'} )
      if try_int(config["airdrop"]["by_reimbursement"]["third"]["from_tx"])<0:
        return jsonify( { 'error': 'airdrop_reimbursment_3_must_be_greater_zero'} )
      if try_int(config["airdrop"]["by_reimbursement"]["third"]["to_tx"])<0:
        return jsonify( { 'error': 'airdrop_reimbursment_3_to_must_be_greater_zero'} )
        
      if try_int(config["airdrop"]["by_reimbursement"]["first"]["from_tx"])>try_int(config["airdrop"]["by_reimbursement"]["second"]["from_tx"]):
        return jsonify( { 'error': 'airdrop_reimbursment_1_not_minor_than_2'} )
      if try_int(config["airdrop"]["by_reimbursement"]["second"]["from_tx"]) >= try_int(config["airdrop"]["by_reimbursement"]["third"]["from_tx"]):
        return jsonify( { 'error': 'airdrop_reimbursment_2_not_minor_than_3'} )
      if try_int(config["airdrop"]["by_reimbursement"]["third"]["from_tx"]) > try_int(config["airdrop"]["by_reimbursement"]["third"]["to_tx"]):
        return jsonify( { 'error': 'airdrop_reimbursment_3_from_not_minor_than_3_to'} )
      
      config["airdrop"]["by_reimbursement"]["first"]["to_tx"] = config["airdrop"]["by_reimbursement"]["second"]["from_tx"]
      config["airdrop"]["by_reimbursement"]["second"]["to_tx"] = config["airdrop"]["by_reimbursement"]["third"]["from_tx"]

      if try_int(config["airdrop"]["by_reimbursement"]["first"]["tx_amount_percent_refunded"] ) <0 or try_int(config["airdrop"]["by_reimbursement"]["first"]["tx_amount_percent_refunded"] ) >100:
        return jsonify( { 'error': 'airdrop_reimbursment_1_perc_between_0_100'} )
      if try_int(config["airdrop"]["by_reimbursement"]["second"]["tx_amount_percent_refunded"] ) <0 or try_int(config["airdrop"]["by_reimbursement"]["second"]["tx_amount_percent_refunded"] ) >100:
        return jsonify( { 'error': 'airdrop_reimbursment_2_perc_between_0_100'} )
      if try_int(config["airdrop"]["by_reimbursement"]["third"]["tx_amount_percent_refunded"] ) <0 or try_int(config["airdrop"]["by_reimbursement"]["third"]["tx_amount_percent_refunded"] ) >100:
        return jsonify( { 'error': 'airdrop_reimbursment_3_perc_between_0_100'} )
      
      if try_int(config["airdrop"]["by_referral"]["referred_amount"]) < 0:
        return jsonify( { 'error': 'airdrop_referral_referred_amount_must_be_greater_or_equal_zero'} )
      if try_int(config["airdrop"]["by_referral"]["referred_max_quantity"])<0:
        return jsonify( { 'error': 'airdrop_referral_referred_max_quantity_must_be_greater_or_equal_zero'} )
      if try_int(config["airdrop"]["by_referral"]["referrer_amount"])<0:
        return jsonify( { 'error': 'airdrop_referral_referrer_amount_must_be_greater_or_equal_zero'} )
      
#       "airdrop": {
#             "by_referral": {
#                 "referred_amount": 25,
#                 "referred_max_quantity": 5,
#                 "referrer_amount": 25
#             },  
    
      with session_scope() as db:
        nm, is_new = get_or_create(db, NameValue, name  = 'configuration')
        nm.value = config
        nm.updated_at = datetime.utcnow()
        db.add(nm)
        db.commit()
      return jsonify( {'ok':'ok'} )
  
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
  
  @app.route('/api/v3/dashboard/business/search', methods=['POST'])
  def search_business():
#     init_model.init_categories()
#     init_model.init_businesses()
#     init_model.init_discount_schedule()
      
    # TODO: procesar cada comercio, y listar tambien montos refunded(out) y discounted (in), historicos
    with session_scope() as db:
#       my_or = or_(Business.category.in_(filter.selected_categories), Business.subcategory.in_(filter.selected_categories))
#       query = db.query(Business).filter(my_or).order_by(Business.id.desc())
      query = db.query(Business).order_by(Business.id.desc())
      bussinesses = [ build_business(x) for x in query.all()] 
      return jsonify( { 'businesses': bussinesses,
                        'total':  len(bussinesses)} )
    
  @app.route('/api/v3/dashboard/business/credited/<skip>/<count>', methods=['GET', 'POST'])
  def business_credited(skip, count):

    default_filter  = { 
      'selected_categories' : [], 
      'search_text'         : '',
      'filter'              : { 'payment_methods': ['cash', 'debit_card', 'credit_card'], 'credited': 'credited' },
      'order'               : { 'field': 'discount', 'date':'monday' }
    }    
    filter          = default_filter

    if request.method=='POST':
      filter = request.json.get('filter', default_filter)
      if 'filter' not in filter:
        filter['filter'] = { 'payment_methods': ['cash', 'debit_card', 'credit_card'], 'credited': 'credited' }
      if 'credited' not in filter['filter']:
        filter['filter']['credited'] = 'credited'

    return jsonify (filter_businesses(skip, count, filter, build=True))

  @app.route('/api/v3/dashboard/business/filter/<skip>/<count>', methods=['GET', 'POST'])
  def business_filter(skip, count):

    default_filter  = { 
                        'selected_categories' : [], 
                        'search_text'         : '',
                        'filter'              : { 'payment_methods': ['cash', 'debit_card', 'credit_card'], 'credited': None },
                        'order'               : { 'field': 'discount', 'date':'monday' }
                      }   

    filter          = default_filter
    if request.method=='POST':
      filter = request.json.get('filter', default_filter)
      
    return jsonify (filter_businesses(skip, count, filter, build=True))
      # return jsonify( { 'businesses': [ x.to_dict() for x in q.all()] } )
      # return jsonify( { 'businesses': [ build_business(x) for x in q.all()] , 'total':total} )
  
  def filter_businesses(skip, count, filter, build=False):
    # TODO: procesar cada comercio, y listar tambien montos refunded(out) y discounted (in), historicos
    print ( ' *** filter_businesses:: and the filter is....', json.dumps(filter))
    with session_scope() as db:
#       sub_stmt = db.query(BusinessCredit.business_id)
      q = db.query(Business)
#       q = q.filter(Business.id.in_(sub_stmt))
      if 'selected_categories' in filter and len(filter['selected_categories'])>0:
        my_or = or_(Business.category_id.in_(filter['selected_categories']), Business.subcategory_id.in_(filter['selected_categories']))
        q = q.filter(my_or)
      
      if 'search_text' in filter and filter['search_text']:
        txt   = '%{0}%'.format(filter['search_text'])
        my_or = or_(Business.name.like(txt), Business.description.like(txt))
        q     = q.filter(my_or)

      if 'filter' in filter and filter['filter']:
        _filter = filter['filter']
        if 'credited' in _filter and _filter['credited'] and _filter['credited']!='':
          # OPTIONS: '' | 'no_credit' | 'overdraft_send' | 'credited'
          if 'no_credit'==_filter['credited']:
            sub_stmt = db.query(BusinessCredit.business_id)
  #           q = q.filter(~Business.id.in_(sub_stmt))
            q = q.filter(Business.id.notin_(sub_stmt))
          if 'overdraft_send'==_filter['credited']:
             pass
          if 'credited'==_filter['credited']:
            sub_stmt = db.query(BusinessCredit.business_id)
            q = q.filter(Business.id.in_(sub_stmt))
      
      if 'order' in filter and filter['order']:
        _order = filter['order']
        if _order['field']=='discount':
          q = q.join(DiscountSchedule, DiscountSchedule.business_id==Business.id)
          q = q.filter(DiscountSchedule.date==_order['date'])
          q = q.order_by(DiscountSchedule.discount.desc())
        if _order['field']=='reward':
          q = q.join(DiscountSchedule, DiscountSchedule.business_id==Business.id)
          q = q.filter(DiscountSchedule.date==_order['date'])
          q = q.order_by(DiscountSchedule.reward.asc())
      q = q.order_by(Business.id.desc())
      total = q.count()
      q = q.limit(count).offset(skip)

      if build:
        return { 'businesses': [ build_business(x) for x in q.all()] , 'total':total}
      return { 'businesses': [ x.to_dict() for x in q.all()] , 'total':total}


  # @app.route('/api/v3/dashboard/business/list/<skip>/<count>', methods=['GET'])
  # def dashboard_business(skip, count):
  #   # TODO: procesar cada comercio, y listar tambien montos refunded(out) y discounted (in), historicos
  #   with session_scope() as db:
  #     return jsonify( { 'businesses': [ build_business(x) for x in db.query(Business).order_by(Business.id.desc()).all()] } )
  
  def build_business(biz):
    business                              = biz.to_dict()
    business['discount_ex']               = { x['date']:{'discount': str(x['discount']), 'reward': str(x['reward']), 'pm_cash':x['pm_cash'], 'pm_debit':x['pm_debit'], 'pm_credit':x['pm_credit'], 'pm_mercadopago':x['pm_mercadopago']} for x in business['discount_schedule']}
    business['balances']                  = get_business_balances(biz.account_id)
    business['rating']                    = get_business_rate(biz.account_id)
    business['avg_discount_by_category']  = get_avg_discount_by_category(biz.category_id, biz.subcategory_id)
    return business
  
  def get_business_balances(account_id):
    assets = [DISCOIN_ID, DISCOIN_CREDIT_ID, DISCOIN_ACCESS_ID]
    p = rpc.db_get_account_balances(account_id, assets)
    the_assets = {}
    for asset in assets:
      the_assets[asset] = cache.get_asset(asset)
    bal = {
      'balance'         : next(( amount_value(x['amount'], the_assets[x['asset_id']]) for x in p if x['asset_id'] == DISCOIN_ID), None), 
      'initial_credit'  : next(( amount_value(x['amount'], the_assets[x['asset_id']]) for x in p if x['asset_id'] == DISCOIN_CREDIT_ID), None), 
      'ready_to_access' : next(( amount_value(x['amount'], the_assets[x['asset_id']]) for x in p if x['asset_id'] == DISCOIN_ACCESS_ID), None)
    }
    print( '================================== get_business_balances #3')
    return bal
  
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
  
  
  
  import os
  BASE_DIR        = os.path.abspath(os.path.dirname(__file__))  
  UPLOAD_FOLDER   = os.path.join(BASE_DIR, 'static/uploads')
  
  def save_image(business_id, image_str, post_fix):
    if not image_str or (not image_str.startswith( 'data:image/png;base64' ) and not image_str.startswith('data:image/jpeg;base64') ):
      return image_str
    import base64
    ext       = 'png' if image_str.startswith( 'data:image/png;base64' ) else 'jpeg'
    filename  = '{0}{1}.{2}'.format(business_id, post_fix, ext) # I assume you have a way of picking unique filenames
    filepath  = os.path.join(UPLOAD_FOLDER, filename)
    print(' --------------- BASE_DIR:', BASE_DIR, ' | UPLOAD_FOLDER:', UPLOAD_FOLDER)
    fh        = open(filepath, "wb")
#     imgdata = base64.decodestring(image_str.replace('data:image/png;base64,','').encode())
    image_str = image_str.replace('data:image/png;base64,','').replace('data:image/jpeg;base64,','')
    fh.write(base64.b64decode(image_str))
    fh.close()
    return filename
  
  
  @app.route('/files/<path:path>')
  def files(path):
    return send_from_directory(UPLOAD_FOLDER, path)

  @app.route('/api/v3/dashboard/business/profile/<account_id>/update', methods=['GET', 'POST'])
  def dashboard_update_business_profile(account_id):
    
    #ToDo: Validar el secret!!!!
    # por business y por admin
    the_secret_text = '{0}_{1}'.format(very_secret_text, account_id)
    
    if request.method=='GET':
      with session_scope() as db:
        return jsonify( { 'business': db.query(Business).filter(Business.account_id==account_id).first().to_dict_for_update(), 'secret' : the_secret_text } );
      
    biz_json           = request.json.get('business')
    signed_secret      = request.json.get('signed_secret')
#       owner           = str( biz_json.get('owner', '') )
#       active          = str( biz_json.get('active', '') )
#       memo            = str( biz_json.get('memo', '') )
#     print ( json.dumps(biz_json))
    with session_scope() as db:
      biz = db.query(Business).filter(Business.account_id==account_id).first()
      if not biz:
        return jsonify( { 'error' : 'account_id_not_found'} )
#         # Elimino la tabla de descuentos del negocio.
#         db.query(DiscountSchedule).filter(DiscountSchedule.business_id==account_id).delete(synchronize_session='fetch')
      errors = biz.validate_dict(biz_json, db)
      if len(errors)>0:
        return jsonify( { 'error' : 'errors_occured', 'error_list':errors } )

#       biz.discount_schedule[:] = []
      
      biz.from_dict_for_update(biz_json)
      filename = save_image(biz.account_id, biz.image, '')
      biz.image = filename
      filename = save_image(biz.account_id, biz.logo, '_logo')
      biz.logo = filename
      
      db.add(biz)
      print (' -- biz.category', biz.category.discount)
#       for schedule in biz_json.get('discount_schedule', []):
#         dis_sche = DiscountSchedule()
#         try:
#           print('--schedule: QuE VINO?', schedule)
#           dis_sche.from_dict(biz.id, schedule, biz.category.discount)
#         except Exception as e:
#           print('--schedule: HAY ERROR!!', str(e))
#           errors.append({'field':'discount_schedule', 'error':str(e)})
#         db.add(dis_sche)
      if len(errors)>0:
        db.rollback()
        return jsonify( { 'error' : 'errors_occured', 'error_list':errors } )
      db.commit()

    return jsonify({'ok':'ok'})

  @app.route('/api/v3/dashboard/business/schedule/<account_id>/update', methods=['GET', 'POST'])
  def dashboard_update_business_schedule(account_id):
    #ToDo: Validar el secret!!!!
    # por business y por admin
    the_secret_text = '{0}_{1}'.format(very_secret_text, account_id)
    
    if request.method=='GET':
      with session_scope() as db:
        return jsonify( { 'business': db.query(Business).filter(Business.account_id==account_id).first().to_dict_for_update(), 'secret' : the_secret_text } );
    
    # {"account_id":"1.2.20","payments":["cash","debit","credit"],"discount_schedule":[{"date":"monday","reward":20,"discount":20},{"date":"tuesday","reward":20,"discount":20},{"date":"wednesday","reward":20,"discount":20},{"date":"thursday","reward":20,"discount":20},{"date":"friday","reward":20,"discount":20},{"date":"saturday","reward":20,"discount":20},{"date":"sunday","reward":20,"discount":20}]}
    discount_schedule_json = request.json.get('discount_schedule')
    signed_secret          = request.json.get('signed_secret')
    errors = []
    with session_scope() as db:
      biz = db.query(Business).filter(Business.account_id==account_id).first()
      if not biz:
        return jsonify( { 'error' : 'account_id_not_found'} )
#         # Elimino la tabla de descuentos del negocio.
#         db.query(DiscountSchedule).filter(DiscountSchedule.business_id==account_id).delete(synchronize_session='fetch')
      
      biz.discount_schedule[:] = []
      print (' -- biz.category', biz.category.discount)
      for schedule in discount_schedule_json.get('discount_schedule', []):
        dis_sche = DiscountSchedule()
        try:
          print('--schedule: QuE VINO?', schedule)
          dis_sche.from_dict(biz.id, schedule, biz.category.discount, discount_schedule_json.get('payments', []))
        except Exception as e:
          print('--schedule: HAY ERROR!!', str(e))
          errors.append({'field':'discount_schedule', 'error':str(e)})
        db.add(dis_sche)
      if len(errors)>0:
        db.rollback()
        return jsonify( { 'error' : 'errors_occured', 'error_list':errors } )
      db.commit()

    return jsonify({'ok':'ok'})

  
  very_secret_text  = 'thisisaveryverysecrettext123456789'
  # Login
  @app.route('/api/v3/<account_type>/login/<account_name>', methods=['GET', 'POST'])
  def business_login(account_type, account_name):
    
    if account_type not in ['business', 'admin']:
      return jsonify( { 'error': 'not_a_valid_account_type' } )
    
    account, account_namex = get_account_impl(account_name)
    if not account:
      return jsonify( { 'error': 'not_a_valid_account' } )
    
    the_secret = '{0}_{1}'.format(very_secret_text, account['name'])
    
    print (request.method, the_secret)
    if request.method=='GET':
      return jsonify( { 'secret': the_secret, 
                        'destintation_key' : rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['options']['memo_key']} )
    
    memo_key      = rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['options']['memo_key']
    memo_from     = str(request.json.get('from'))
    memo_to       = str(request.json.get('to'))
    memo_nonce    = 0
    memo_message  = str(request.json.get('signed_secret'))
    
    if not account['options']['memo_key']==memo_from:
      print (' ==== LOGIN ERROR:', 'invalid_sender_memo_key')
      return jsonify( { 'error': 'invalid_sender_memo_key' } )
    
    if memo_key!=memo_to:
      print (' ==== LOGIN ERROR:', 'invalid_destination_memo_key')
      return jsonify( { 'error': 'invalid_destination_memo_key' } )
    
    print( memo_from,  memo_to, memo_nonce, memo_message)
    dec = decode_memo(  PrivateKey(REGISTER_PRIVKEY),
                        PublicKey(memo_from, prefix='BTS'),
                        0,
                        memo_message)
#     print (account)
#     print (account_namex )
    print( '==== LOGIN::DECODE_MEMO:', dec)
    return jsonify( { 'decrypted_secret' : str(dec), 'login' : dec==the_secret, 'account' : account } )
  
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # Subaccount Management
  # =================================================================================================
  
  # Lista las subcuentas de un business.
  @app.route('/api/v3/business/<business_id>/subaccount/list/<start>', methods=['GET', 'POST'])
  def business_subaccount_list(business_id, start):
#     print( ' == get_withdraw_permissions_by_giver:')
#     if not start or str(start).strip()=='0':
#       start = '1.12.0'
#     perms = rpc.db_get_withdraw_permissions_by_giver(business_id, start, 100)
#     subaccounts = []
#     for perm in perms:
#       # Check if account already added???
#       subaccounts.append( build_subaccount ( cache.get_account(perm['authorized_account']), perm ) )
#     return jsonify( { 'subaccounts': subaccounts, 'permissions' : perms} )
    ret = business_subaccount_list_impl(business_id, start, True)
    return jsonify( { 'subaccounts': ret['subaccounts'], 'permissions' : ret['perms']} )
  
  def business_subaccount_list_impl(business_id, start, build_subaccounts):
    print( ' == get_withdraw_permissions_by_giver:')
    if not start or str(start).strip()=='0':
      start = '1.12.0'
    perms = rpc.db_get_withdraw_permissions_by_giver(business_id, start, 100)
    subaccounts = []
    for perm in perms:
      # Check if account already added???
      if build_subaccounts:
        subaccounts.append( build_subaccount ( cache.get_account(perm['authorized_account']), perm ) )
      else:
#         print(' ---- business_subaccount_list_impl', json.dumps(perm['authorized_account']))
        subaccounts.append( perm['authorized_account'])
    return {'subaccounts':subaccounts, 'perms':perms}
  
  def build_subaccount(account, perm):
    asset = rpc.db_get_assets([DISCOIN_ID])[0]
    return { 
      'name'        : account['name'],  
      'id'          : account['id'],
      'amount'      : amount_value(perm['withdrawal_limit']['amount'], asset), 
      'expiration'  : perm['expiration'],  
      'since'       : perm['period_start_time'],
      'interval'    : perm['withdrawal_period_sec'],
      'claimed_this_period' : perm['claimed_this_period']
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
    
    # print( ' == subaccount_add_or_update_create_impl #1')
    # Check if business has credit.
    p = rpc.db_get_account_balances(business_id, [DISCOIN_CREDIT_ID])
    if p[0]['amount'] <= 0:
      return {'error':'business_has_no_credit'}
    # Check if subaccount is valid account.
    # print( ' == subaccount_add_or_update_create_impl #2')
    subaccounts = rpc.db_get_accounts([subaccount_id])
    if not subaccounts or len(subaccounts)==0:
      return {'error': 'subaccount_not_exists'}
    
    # print( ' == subaccount_add_or_update_create_impl #2')
    # Validamos que la subaccount_id no tenga ya permisos de withdraw por parte del comercio:
    perm = get_withdraw_permission(business_id, subaccount_id)
#     if perm:
#       return {'error': 'subaccount_id_already_has_permission'}
      
    # print( ' ======================================================')
    # print (' ====== subaccount_add_or_update_create_impl #3')
    asset, asset_core = rpc.db_get_assets([DISCOIN_ID, CORE_ASSET])
    
    # ~ie:<%y%m%d>:<1.2.1526>:25000
    if not _from:
      _from = (datetime.utcnow()+timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%S')
      # print(' ----- SUBCUENTA::datetime.utcnow::', _from) 
    else:
      _from = datetime.fromtimestamp(try_int(_from)).strftime('%Y-%m-%dT%H:%M:%S')
      # print(' ----- SUBCUENTA::datetime.fromtimestamp:', _from) 
    if not period:
      period = 86400 # 1 day in seconds
    if not periods:
      periods = 365 # 365 periods = 1 year
    
    if homedir=='/home/tuti':
      # print(' ----- SUBCUENTA::datetime.utcfromtimestamp:[PRE]', _from) 
      _from_loaded = datetime.strptime(_from, '%Y-%m-%dT%H:%M:%S')
      # print(' ----- SUBCUENTA::datetime.utcfromtimestamp:[LOADED]', _from_loaded) 
      _from        = (_from_loaded+timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%S')
      # print(' ----- SUBCUENTA::datetime.utcfromtimestamp:[POST]', _from) 
    my_amount = reverse_amount_value(limit, asset)
    my_amount_asset = {
      'amount'  : my_amount,
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
    
    # print( ' == fees: ')
    # print (fees)
    # print (' == Calc fee')
    # print (amount_value(fees[0]['amount'], asset_core))
    
    _transfer = transfer(
        DISCOIN_ADMIN_ID,
        business_id,
        asset_core,
        amount_value(fees[0]['amount'], asset_core),
        '',
        None,
        CORE_ASSET
    )
#     print( ' == transfer: ')
#     print (_transfer)
    
    
#     _transfer +
#     [_transfer[0]]\
    print (' ---------- ABOUT TO  build_tx_and_broadcast')
    tx = build_tx_and_broadcast(
      _transfer + [withdraw_permission_op[0]] 
    , None)
    
    print (' ---------- ADD SUBACCOUNT', json.dumps(tx))
    return extern_sign_tx(tx, REGISTER_PRIVKEY)['tx']
#     to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
#     signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
#     tx['signatures'] = [signature]
#     return tx
  
  # =================================================================================================
  # =================================================================================================
  # =================================================================================================
  # Claim daily Withdraw & Refund
  # =================================================================================================
  @app.route('/api/v3/business/subaccount/withdraw/daily', methods=['POST'])
  def withdraw_daily_amount():
    # curl -H "Content-Type: application/json" -X POST -d '{"business_id" : "1.2.25", "subaccount_id" : "1.2.27", "to" : "1.2.19", "amount" : 500, "bill_amount" : 2000, "bill_id" : "this_is_a_bill_id"}' http://35.163.59.126:8080/api/v3/business/subaccount/refund/create  
    business_id     = request.json.get('business_id')
    subaccount_id   = request.json.get('subaccount_id')
    tx              = withdraw_daily_amount_impl(business_id, subaccount_id)
    return jsonify( {'tx':tx} )
  
  def withdraw_daily_amount_impl(business_id, subaccount_id):
    perms = rpc.db_get_withdraw_permissions_by_recipient(subaccount_id, '1.12.0', 100) 
    the_perm = None
    for perm in perms:
      print(' -- withdraw_daily_amount::perm', json.dumps(perm))
      print (' --- withdraw_from_account:', perm["withdraw_from_account"] ,'==', business_id )
      print (' --- expiration:', perm["expiration"] ,'>', datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') )
      print (' --- period_start_time:', perm["period_start_time"] , '<=' , datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') )
      print (' --- withdrawal_limit:', perm["withdrawal_limit"]["asset_id"], '==', DISCOIN_ID)
      if perm["withdraw_from_account"] == business_id and perm["expiration"] > datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') and perm["period_start_time"] <= datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S') and perm["withdrawal_limit"]["asset_id"]==DISCOIN_ID:
        the_perm = perm
        break
      else:
        print(' -- withdraw_daily_amount::perm NOT VALID', json.dumps(perm))  
    print(' -- withdraw_daily_amount::the_perm', json.dumps(the_perm))
    if not the_perm:
      return None
    
    asset, asset_core = rpc.db_get_assets([DISCOIN_ID, CORE_ASSET])
    withdraw_permission_claim_op = withdraw_permission_claim(perm['id'], business_id, subaccount_id, perm["withdrawal_limit"], None, CORE_ASSET)
    #withdraw_permission_claim_op = withdraw_permission_claim(perm['id'], business_id, subaccount_id, perm["withdrawal_limit"], None, DISCOIN_ID)


    fees = rpc.db_get_required_fees([withdraw_permission_claim_op[0]] , CORE_ASSET)
    #fees = rpc.db_get_required_fees([withdraw_permission_claim_op[0]] , DISCOIN_ID)

    _transfer = transfer(
        DISCOIN_ADMIN_ID,
        subaccount_id,
        asset_core,
        amount_value(fees[0]['amount'], asset_core)
      )

    tx = build_tx_and_broadcast(
        [_transfer[0]] + [withdraw_permission_claim_op[0]]
       # [withdraw_permission_claim_op[0]]
        , None)

#     to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
#     signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
#     tx['signatures'] = [signature]
#     return tx
    return extern_sign_tx(tx, REGISTER_PRIVKEY)['tx']
  
  
  @app.route('/api/v3/refund/create', methods=['POST'])
  def refund_create():
    from_id         = request.json.get('from_id')
    to_id           = request.json.get('to_id')  
    amount          = request.json.get('amount')  
    bill_amount     = request.json.get('bill_amount')  
    bill_id         = request.json.get('bill_id')  
    
    tx = refund_create_impl(from_id, to_id, amount, bill_amount, bill_id)
    
    return jsonify( tx )
  
  def refund_create_impl(from_id, to_id, amount, bill_amount, bill_id):
    
    asset, asset_core = rpc.db_get_assets([DISCOIN_ID, CORE_ASSET])
    
    my_amount = reverse_amount_value(amount, asset)
    my_amount_asset = {
      'amount'   : my_amount,
      'asset_id' : DISCOIN_ID
    }
    
    utc_now = datetime.utcnow().strftime('%y%m%d')
    memo = {
#       'message' : '~re:{0}:{1}:{2}'.format(utc_now, bill_amount, bill_id).encode('hex')
#       'message' : binascii.hexlify('~re:{0}:{1}:{2}'.format(utc_now, bill_amount, bill_id).encode()).decode('utf-8')
      'message' : binascii.hexlify('~re:{0}:{1}'.format(bill_amount, bill_id).encode()).decode('utf-8')
    }
    
    _refund = transfer(
        from_id,
        to_id,
        asset,
        amount,
        memo,
        None,
        DISCOIN_ID
    )
    print( ' == refund: ')
    print (_refund)
    
    #fees = rpc.db_get_required_fees([_refund[0]] , CORE_ASSET)
    #fees = rpc.db_get_required_fees([_refund[0]] , DISCOIN_ID)
    #print (' == fees: ')
    #print (fees)
    
    #_transfer = transfer(
    #    DISCOIN_ADMIN_ID,
    #    from_id,
    #    asset_core,
    #    amount_value(fees[0]['amount'], asset_core)
    #  )
    #print (' == transfer: ')
    #print (_transfer)
    
    # _transfer + _refund
    tx = build_tx_and_broadcast(
      _refund
    , None)
    
#     to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
#     signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
#     tx['signatures'] = [signature]
    
#     return extern_sign_tx(tx, REGISTER_PRIVKEY)
    return {'tx':tx}

  # =================================================================================================
  # =================================================================================================
  
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

    #tx = subaccount_refund_impl(business_id, subaccount_id, _to, amount, bill_amount, bill_id)
    tx = {'error': 'subaccount_has_no_permission'}
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
#     print (' === subaccount_refund_impl #2.5', my_amount)
    my_amount_asset = {
      'amount'   : my_amount,
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
    if try_int(initial_credit)<=0 or try_int(initial_credit)>100000:
      return jsonify( {'error': 'MIN:1, MAX:100.000'})
    
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
#       'message' : '~ie:{0}:{1}:{2}'.format(utc_now, business_id, initial_credit).encode('hex')
      'message' : binascii.hexlify('~ie:{0}:{1}:{2}'.format(utc_now, business_id, initial_credit).encode()).decode('utf-8')
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
    
    if not business_name.startswith(ACCOUNT_PREFIX):
      business_name = ACCOUNT_PREFIX+business_name
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
#       'message' : '~ae'.encode('hex')
      'message' : binascii.hexlify(b'~ae').decode('utf-8')
    }
    
#     print( ' ==== ACCESS BALANCE:')
#     print( access_balance[0]['amount'])
    
    apply_transfer_op = transfer(
      business_id,
      DISCOIN_ADMIN_ID,
      asset,
      access_balance[0]['amount'],
      memo,
      None,
      CORE_ASSET
    )[0]

#     print( "************************************************")
#     print( json.dumps(apply_transfer_op, indent=2))
#     print( "*********************")

#     # fees = rpc.db_get_required_fees([endorse_transfer_op], CORE_ASSET)
#     print( "toma => ", apply_transfer_op[1]['fee']['amount'])
#     print( "************************************************")

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

#     to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
#     signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    print (' ###################################### endorse_apply')
    print (tx)
    signed_tx = extern_sign_tx(tx, REGISTER_PRIVKEY)
    print (tx)
#     tx['signatures'] = [signature]
    return signed_tx['tx']
  
  
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
  
  #ToDo:
  @app.route('/api/v3/business/category/list', methods=['GET'])
  def dashboard_category_list():
    with session_scope() as db:
      q = db.query(Category)
      q = q.order_by(Category.parent_id)
      return jsonify( {'categories' : [ c.to_dict(zero_if_parent_id_null=True) for c in q.all()] } )
      
  #ToDo:
  @app.route('/api/v3/business/category/add_or_update', methods=['POST'])
  def dashboard_category_add_update():
    cat  = request.json.get('category')
#     a = {
#       'id'          : 
#       'name'        : 
#       'description' : 
#       'parent_id'   : 

#       'discount'    : 
#     }
    
#     if cat['id'] and is_number(cat['id']):
    cat_id = 0
    if 'id' in cat and is_number(cat['id']):
      cat_id = try_int(cat['id'])  
#     db_cat = None
    with session_scope() as db:
      db_cat = Category()
      if cat_id>0:
        db_cat, is_new = get_or_create(db, Category, id  = cat_id)
      db_cat.from_dict(cat)
      db.add(db_cat)
      db.flush()
      cat_dict = db_cat.to_dict()
#       db.refresh(db_cat)
      db.commit()
#       db.expunge(db_cat)
      return jsonify( {'ok':'ok', 'category' : cat_dict } )
  
  @app.route('/api/v3/business/category/delete', methods=['POST'])
  def dashboard_category_delete():
    cat_id  = request.json.get('id')
    if not cat_id or not is_number(cat_id):
      return jsonify( {'error':'id_not_a_number'})
    with session_scope() as db:
      try:
        db.query(Category).filter(Category.id == cat_id).delete(synchronize_session=False)
      except Exception as e:
        db.rollback()
        return jsonify( {'error':str(e)})
      db.commit()
    return jsonify( {'ok':'ok'})
    
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
      data = [ c.to_dict(zero_if_parent_id_null=True) for c in q2.all()] 
#       print (' ============== query result:')
#       print (json.dumps(data))
#       print (' ============== END!')
    return jsonify( {"categories":data} )
  
#   select * from  category where isnull(parent_id) order by name desc;

  @app.route('/api/v3/push_id', methods=['POST'])
  def push_id():
    # curl -H "Content-Type: application/json" -X POST -d '{"name":"fake.name","push_id":"qwertyasdfg"}' http://35.163.59.126:8080/api/v3/push_id
    with session_scope() as db:
      pi, is_new = get_or_create(db, PushInfo,
        name  = request.json.get('name'),
      )
      pi.push_id    = request.json.get('push_id')
      pi.version    = request.json.get('version', '0')
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
    
    tx = extern_sign_tx(tx, priv_key)    
    # res = extern_push_tx(tx['tx'])
    # return jsonify( res )
    res = rpc.network_broadcast_transaction_sync(tx['tx'])
    print( json.dumps(res, indent=2))
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
    account_ids = list(set(rpc.db_get_key_references([key])[0]))
    print (' == account_ids : ')
    print (account_ids)
    names = [real_name(a['name']) for a in rpc.db_get_accounts(account_ids)]
    res = []
    if len(account_ids)>0 and len(names)>0:
      res.append(names[0])
      res.append(account_ids[0])
      res.append(getIdenticonForAccount(names[0]))
    print (' == res : ')
    print (json.dumps(res) )
    return jsonify(res)

  @app.route('/api/v3/account/by_name/<account>', methods=['GET'])
  def get_account(account):
    res, account_name = get_account_impl(account)
    if not res:
      return jsonify(  {'res': 'account_not_found', 'error':1})
    return jsonify( {"res": res}  )
  
  @app.route('/api/v3/business/by_name/<account>', methods=['GET'])
  def get_business(account):
    res, account_name = get_account_impl(account)
    if not res:
      return jsonify(  {'res': 'account_not_found', 'error':1})
    with session_scope() as db:
      biz = db.query(Business).filter(Business.account==account_name).first()
      if not biz:
        return jsonify( { 'error' : 'account_id_not_found'} )
      return jsonify( { "account": res, 'discount_schedule' : [x.to_dict() for x in biz.discount_schedule] if biz.discount_schedule else []} );
  
  @app.route('/api/v3/business/by_account_id/<account_id>', methods=['GET'])
  def get_business_by_id(account_id):
    obj = rpc.db_get_accounts([account_id])
    
    if not obj:
      return jsonify(  {'res': 'account_not_found', 'error':1})
    with session_scope() as db:
      biz = db.query(Business).filter(Business.account_id==account_id).first()
      if not biz:
        return jsonify( { 'error' : 'account_id_not_found'} )
      #, 'discount_schedule' : [x.to_dict() for x in biz.discount_schedule] if biz.discount_schedule else []} 
      # "account": obj, 
      return jsonify( { "business": biz.to_dict() });
    
  
  
  def get_account_impl(account):
    if str(account) != str(DISCOIN_ADMIN_NAME):
      if not account.startswith(ACCOUNT_PREFIX):
        account = ACCOUNT_PREFIX+account
    obj = rpc.db_get_account_by_name(account)
    return (obj, account)
    
  
  @app.route('/api/v3/account/search2', methods=['GET'])
  def search_account2():
    # OLD searchAccount
    search = request.args.get('search', '')
    search_filter = try_int(request.args.get('search_filter',0))
    
    if search=='*':
      search=''
    
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
#           print( '=== Account: ')
#           print (tmp[0])
          # Only with no-credit and no black-listed
          if search_filter == 1:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
#             print( '=== Overdraft: ')
#             print (p[0]['amount'])
            no_credit = p[0]['amount'] == 0
            no_black = tmp[1] not in rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['blacklisted_accounts']
            add_account = no_credit and no_black
          
          # Only with credit
          if search_filter == 2:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
            has_credit = p[0]['amount'] > 0
            #no_black = tmp[1] not in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']
            add_account = has_credit
          if add_account:
            item = []
            item.append(ACCOUNT_PREFIX + tmp[0]) 
            item.append(tmp[1])
            item.append(getIdenticonForAccount(item[0]))
            res.append( item )
    print (json.dumps(res))
    return jsonify( {'res' : res} )
  
  
  @app.route('/api/v3/account/search', methods=['GET'])
  def search_account():
    # OLD searchAccount
    search = request.args.get('search', '')
    search_filter = try_int(request.args.get('search_filter',0))
    
    if search=='*':
      search=''
    
    print(' -- search:',search,' -- search_filter:',search_filter)
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
#           print( '=== Account: ')
#           print (tmp[0])
          # Only with no-credit and no black-listed
          if search_filter == 1:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
#             print( '=== Overdraft: ')
#             print (p[0]['amount'])
            no_credit = p[0]['amount'] == 0
            no_black = tmp[1] not in rpc.db_get_accounts([DISCOIN_ADMIN_ID])[0]['blacklisted_accounts']
            add_account = no_credit and no_black
          
          # Only with credit
          if search_filter == 2:
            p = rpc.db_get_account_balances(tmp[1], [DISCOIN_CREDIT_ID])
            has_credit = p[0]['amount'] > 0
            #no_black = tmp[1] not in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']
            add_account = has_credit
          if add_account:
            tmp[0] = ACCOUNT_PREFIX + tmp[0]
            res.append( tmp )
    print (json.dumps(res))
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
      
#       if not bts2helper_is_valid_name(name):
#         return jsonify({'error': 'is_not_valid_account_name'})

#       if not bts2helper_is_cheap_name(name):
#         return jsonify({'error': 'is_not_cheap_account_name'})
      valid_name_errs = extern_validate_name(name)
      if len(valid_name_errs)>0:
        return jsonify(valid_name_errs[0])
      
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

#       to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
      wif = REGISTER_PRIVKEY
#       #### signature = sign_compact2(to_sign, b.encode_privkey(k, 'wif'))
#       signature = bts2helper_sign_compact(to_sign, wif)
#       tx['signatures'] = [signature]
      signed_tx = extern_sign_tx(tx, wif)
      p = rpc.network_broadcast_transaction_sync(signed_tx['tx'])
      print( json.dumps(p, indent=2))
      
      return jsonify({'ok':'ok', 'res':p, 'identicon': getIdenticonForAccount(name), 'account_id':p["trx"]["operation_results"][0][1] })

    except Exception as e:
      logging.error(traceback.format_exc())
      return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)

  def getIdenticonForAccount(account_name):
    if not account_name:
      account_name = 'discoin'
    account_name = account_name.replace(ACCOUNT_PREFIX, '')
    return hashlib.sha512(account_name.encode()).hexdigest()
  
  @app.route('/api/v3/account/identicon', methods=['GET'])
  def account_identicon():
    account_name        = request.args.get('account_name', '').strip()
    return jsonify({'identicon': getIdenticonForAccount(name)})
    
  @app.route('/api/v3/business/register', methods=['POST'])
  def business_register():
#     try:
    req   = request.json
    account_name  = str( req.get('account_name') )
    if not account_name.startswith(ACCOUNT_PREFIX):
      account_name  = ACCOUNT_PREFIX + account_name

    if req.get('secret') == 'cdc1ddb0cd999dbc5ba8d7717e3837f5438af8198d48c12722e63a519e73a38c':
      account_name = str( req.get('account_name') )

    owner  = str( req.get('owner') )
    active = str( req.get('active') )
    memo   = str( req.get('memo') )

#       if not bts2helper_is_valid_name(account_name):
#         return jsonify({'error': 'is_not_valid_account_name'})

#       if not bts2helper_is_cheap_name(account_name):
#         return jsonify({'error': 'is_not_cheap_account_name'})

    print(' --ACCOUNT_NAME ', account_name)
    valid_name_errs = extern_validate_name(account_name)
    print(' --EXTERN CALL valid_name_errs ', valid_name_errs)
    if len(valid_name_errs)>0:
      return jsonify(valid_name_errs[0])

    acc = rpc.db_get_account_by_name(account_name)
    if acc is not None:
      return jsonify({'error': 'already_taken_account_name'})

    name            = str( req.get('name') )
    email           = str( req.get('email') )
    telephone       = str( req.get('telephone') )
#       print(' --NAME ', name, ' --EMAIL ', email, ' --TE ', telephone )
    category_id     = req.get('category_id')
    if not category_id or category_id=='':
#         print ('category is NONE:', category_id)
      category_id = req.get('category')
    subcategory_id  = req.get('subcategory_id')
    if not subcategory_id or subcategory_id=='':
#         print ('subcategory is NONE:', subcategory_id)
      subcategory_id = req.get('subcategory')

    category_id    = str(category_id)
    subcategory_id = str(subcategory_id)
    print ('================== category_id')
    print (category_id)
    print ('================== subcategory_id')
    print (subcategory_id)

    cat = None
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
      db.expunge(cat)
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

#       to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    wif = REGISTER_PRIVKEY
#       signature = bts2helper_sign_compact(to_sign, wif)
#       tx['signatures'] = [signature]
#       res = rpc.network_broadcast_transaction_sync(tx)
    
    print(' ---- register antes de mandar a signar')
    signed_tx = extern_sign_tx(tx, wif)
    res = extern_push_tx(signed_tx['tx'])
    print( json.dumps(res, indent=2))
  
    biz = Business()
    with session_scope() as db:
      biz.email           = email
      biz.name            = name
      biz.telephone       = telephone
      biz.account         = account_name
      biz.description     = name
      biz.discount        = Decimal(cat.discount) # ToDo: traer de categoria
      biz.reward          = Decimal(cat.discount) # ToDo: traer de categoria
      biz.category_id     = category_id
      biz.subcategory_id  = subcategory_id
#         _id = cache.get_account_id( unicode(account_name) )
#         biz.account_id  = str(_id if _id else '')
      biz.account_id      = res["res"]["trx"]["operation_results"][0][1] 
      db.add(biz)
      db.flush()
      db.refresh(biz)
      for schedule in DiscountSchedule.get_defaults(biz.discount, biz.reward, biz.id):
        db.add(schedule)
      db.commit()
    print(' ---- register OK!', json.dumps(res['res'] ))
#       return jsonify({'tx' : tx})
    return jsonify({'ok':'ok', 'res':res['res']})

#     except Exception as e:
#       logging.error(traceback.format_exc())
#       return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)
 
    # weeks, days, months
  def get_last_something(something, raw=False):
    # today = datetime.date.today()
    # first = today.replace(day=1)
    _now      = datetime.utcnow()
    made_now  = datetime(_now.year, _now.month, _now.day)
    the_day   = None
    if something=='days':
      the_day   = (made_now+timedelta(weeks=-1))
    if something=='weeks':
      the_day   = (made_now+timedelta(days=-1))
    if something=='months':
      from dateutil.relativedelta import relativedelta
      the_day   = (made_now+relativedelta(months=-1))
    if raw:
      return the_day
    return the_day.strftime('%Y-%m-%d %H:%M:%S')


  @app.route('/api/v3/business/<account_id>/kpis', methods=['GET', 'POST'])
  def get_processed_data(account_id):
    # subaccounts = [account_id or '1.2.20']
    subaccounts = [account_id] + business_subaccount_list_impl(account_id, 0, False)['subaccounts']
    main_asset = cache.get_asset(DISCOIN_ID)
    with session_scope() as db:
      q = db.query(Transfer)
      
      filter_from = (Transfer.from_id.in_(subaccounts))
      filter_to   = (Transfer.to_id.in_(subaccounts))
      my_or       = or_(filter_to, filter_from)
      q           = q.filter(my_or)

      q           = q.order_by(Transfer.id.desc())
      count       = q.count()
      # q           = q.limit(20).offset(0)
      _last_week_raw  = get_last_something('weeks', True)
      print(' ----------------------- BIZ KPIs', _last_week_raw)
      q           = q.filter(Transfer.timestamp>_last_week_raw)

      filter_reward            = (Transfer.tx_type=='refund')
      filter_discount          = (Transfer.tx_type=='discount')
      total_rewarded           = db.query(func.sum(Transfer.amount)).filter( filter_reward ).scalar() or 0
      total_billed_rewarded    = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_reward ).scalar() or 0
      total_discounted         = db.query(func.sum(Transfer.amount)).filter( filter_discount ).scalar() or 0
      total_billed_discounted  = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_discount ).scalar() or 0
      
      _last_month              = get_last_something('months')
      monthly_rewards          = db.query(func.sum(Transfer.amount)).filter( filter_reward ).filter(Transfer.timestamp>_last_month).scalar() or 0
      monthly_billed_rewards   = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_reward ).filter(Transfer.timestamp>_last_month).scalar() or 0
      monthly_discounts        = db.query(func.sum(Transfer.amount)).filter( filter_discount ).filter(Transfer.timestamp>_last_month).scalar() or 0
      monthly_billed_discounts = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_discount ).filter(Transfer.timestamp>_last_month).scalar() or 0

      _last_week              = get_last_something('weeks')
      lastw_discounts         = db.query(func.sum(Transfer.amount)).filter( filter_discount ).filter(Transfer.timestamp>_last_week).scalar() or 0
      lastw_billed_discounts  = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_discount ).filter(Transfer.timestamp>_last_week).scalar() or 0
      lastw_rewards           = db.query(func.sum(Transfer.amount)).filter( filter_reward ).filter(Transfer.timestamp>_last_week).scalar() or 0
      lastw_billed_rewards    = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_reward ).filter(Transfer.timestamp>_last_week).scalar() or 0

      _last_day               = get_last_something('days')
      today_discounts         = db.query(func.sum(Transfer.amount)).filter( filter_discount ).filter(Transfer.timestamp>_last_day).scalar() or 0
      today_billed_discounts  = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_discount ).filter(Transfer.timestamp>_last_day).scalar() or 0
      today_rewards           = db.query(func.sum(Transfer.amount)).filter( filter_reward ).filter(Transfer.timestamp>_last_day).scalar() or 0
      today_billed_rewards    = db.query(func.sum(Transfer.tx_bill_amount)).filter( filter_reward ).filter(Transfer.timestamp>_last_day).scalar() or 0
      

      ret = { 'last_week_txs'   : [ c.to_dict_ex(main_asset) for c in q.all()],

              'total_txs'                 : count,
              'total_rewarded'            : amount_value(total_rewarded, main_asset),
              'total_discounted'          : amount_value(total_discounted, main_asset),
              
              'total_billed_rewarded'     : total_billed_rewarded,
              'total_billed_discounted'   : total_billed_discounted,
              
              'monthly_discounts'         : amount_value(monthly_discounts, main_asset),
              'monthly_rewards'           : amount_value(monthly_rewards, main_asset),
              'monthly_billed_discounts'  : monthly_billed_discounts,
              'monthly_billed_rewards'    : monthly_billed_rewards,

              'lastw_discounts'           : amount_value(lastw_discounts, main_asset),
              'lastw_rewards'             : amount_value(lastw_rewards, main_asset),
              'lastw_billed_discounts'    : lastw_billed_discounts,
              'lastw_billed_rewards'      : lastw_billed_rewards,

              'today_discounts'           : amount_value(today_discounts, main_asset),
              'today_rewards'             : amount_value(today_rewards, main_asset),
              'today_billed_discounts'    : today_billed_discounts,
              'today_billed_rewards'      : today_billed_rewards
      }
      
      return jsonify(ret)
    

  # c.count = Session.query(func.count(Person.id)).scalar()

  # c.avg = Session.query(func.avg(Person.id).label('average')).scalar()
 
  # c.sum = Session.query(func.sum(Person.id).label('average')).scalar()
  
  # c.max = Session.query(func.max(Person.id).label('average')).scalar() 

  def get_business_transactions_extended_impl(account_id, skip=0, limit=20):
    
    if not account_id:
      return make_response(jsonify({'error': 'NO_ACCOUNT_ID_PROVIDED'}), 500)
    
    # 1- traemos las subcuentas del comercio via memcached
    subaccounts = business_subaccount_list_impl(account_id, 0, False)['subaccounts']
    
    main_asset = cache.get_asset(DISCOIN_ID)
    # 2- listamos trasnacciones de BBDD
    subaccounts.append(account_id)
    with session_scope() as db:
      q = db.query(Transfer)
      my_or = or_(Transfer.from_id.in_(subaccounts), Transfer.to_id.in_(subaccounts))
      q = q.filter(my_or)
      q = q.order_by(Transfer.id.desc())
      total = q.count()
      q = q.limit(limit).offset(skip)
      return { 'txs': [ c.to_dict_ex(main_asset) for c in q.all()], 'total' : total }
     
  @app.route('/api/v3/business/<account_id>/transactions/list/<skip>/<limit>', methods=['GET', 'POST'])
  def get_business_transactions_extended(account_id, skip, limit):
    # return jsonify( { 'txs' : get_business_transactions_extended_impl(account_id, skip, limit) } )
    return jsonify( get_business_transactions_extended_impl(account_id, skip, limit) )
 
  @app.route('/api/v3/business/<account_id>/transactions/list', methods=['GET', 'POST'])
  def get_business_transactions(account_id):
#     return jsonify( { 'txs' : get_business_transactions_impl(account_id) } )
    # return jsonify( { 'txs' : get_business_transactions_extended_impl(account_id) } )
    return jsonify( get_business_transactions_extended_impl(account_id) )
    
  
  @app.route('/api/v3/get_fees_for_tx', methods=['POST'])
  def get_fees_for_tx():
    tx    = request.json.get('tx')
#     print(' -- get_fees_for_tx:')
    ops = tx['operations']
    fees  = rpc.db_get_required_fees([ops[0]] , DISCOIN_ID)
    return jsonify({'fees':fees})
    
  def extern_sign_tx(tx, pk):
    url = '/api/v3/sign_tx'
    values = {'tx' : tx,
              'pk' : pk}
    print(' --- extern_sign_tx', json.dumps(values))
    return extern_call(values, url)
  
  def extern_push_tx(tx):
    url = '/api/v3/push_tx'
    values = {'tx' : tx}
    print(' --- extern_push_tx', json.dumps(values))
    return extern_call(values, url)
  
  def extern_validate_name(account_name):
    url = '/api/v3/validate_name'
    values = {'account_name' : account_name}
    return extern_call(values, url)
  
  def extern_call(json_object, url):
    
    url = 'http://127.0.0.1:8080' + url
    import requests
    r = requests.post(url, json=json_object)
    print (r.status_code)
    return r.json()

    
    
#     data = urllib.parse.urlencode(json_object)
#     data = data.encode('ascii') # data should be bytes
#     req = urllib.request.Request(url, data)
#     response = urllib.request.urlopen(req)
#     data = response.read()
#     encoding = response.info().get_content_charset('utf-8')
#     json.loads(data.decode(encoding))
    
#     return json
  
  @app.errorhandler(404)
  def not_found(error):
    return make_response(jsonify({'error': 'not_found'}), 404)
  app.config['JSON_AS_ASCII'] = False
  app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT",8088)), threaded=True)
  
