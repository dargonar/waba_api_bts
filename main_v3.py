import os
import sys
import logging
import traceback
import time

from datetime import datetime
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

ERR_UNKNWON_ERROR    = 'unknown_error'

def create_app(**kwargs):
  app = Flask(__name__)
  app.debug = True
  app.add_url_rule('/graphql/v3', view_func=GraphQLView.as_view('graphql', schema=theSchema, **kwargs))

  @app.before_request
  def log_request():
    print ('request.data', request.data)
  
  @app.before_request
  def before_request():
    g.start = time.time()
  
  @app.teardown_request
  def teardown_request(exception=None):
    diff = time.time() - g.start
    print ('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    print ('EL REQUEST TOTAL TOMO =>', diff)
    print ('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    
  CORS(app)
    
  return app

if __name__ == '__main__':
  app = create_app(executor=GeventExecutor(), graphiql=True)
  
  @app.errorhandler(Exception)
  def unhandled_exception(e):
    return make_response(jsonify({'error': str(e)}), 500)
  
#   @app.route('/api/v3/transfer', methods=['POST'])
#   def transfer():
#     try:
#       req = request.json

#       def build_amount( a ):
#         if not a: return None
#         return { "amount": int(Decimal(a)*ASSET_PRECISION), "asset_id" : ASSET_ID }
      
#       print req.get('from')
#       _from  = rpc.db_get_account_by_name( ACCOUNT_PREFIX + req.get('from') )['id']
#       to     = req.get('to')
#       amount = build_amount ( req.get('amount') )
#       memo   = req.get('memo')

#       top = transfer_op(_from, to, amount, memo)
#       top[1]['fee'] = rpc.db_get_required_fees([top], ASSET_ID)[0]
      
#       ref_block_num, ref_block_prefix = ref_block(rpc.db_get_dynamic_global_properties()['head_block_id'])
#       tx = build_tx([top], ref_block_num, ref_block_prefix)
#       to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)

#       return jsonify( {'tx':tx, 'to_sign':to_sign} )
      
#     except Exception as e:
#       logging.error(traceback.format_exc())
#       return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)

  # ############################################    
  # Backend api 
  # ############################################
  # @app.route('/backend/dt/holding', methods=['GET'])
  # def holding():
    
  #   columns = []
  #   columns.append(ColumnDT('id'))
  #   columns.append(ColumnDT('name'))
  #   #columns.append(ColumnDT('address.description')) # where address is an SQLAlchemy Relation
  #   #columns.append(ColumnDT('created_at', filter=str))

  #   # defining the initial query depending on your purpose
  #   query = DBSession.query(AccountBalance) #.join(Address).filter(Address.id > 14)

  #   # instantiating a DataTable for the query and table needed
  #   rowTable = DataTables(request.args, AccountBalance, query, columns)

  #   # returns what is needed by DataTable
  #   return jsonify( rowTable.output_result() )

  @app.route('/api/v3/endorse/apply', methods=['POST'])
  def endorse_create():
    
    valid_assets = [AVAL_1000, AVAL_10000, AVAL_30000]    
    
    _from        = request.json.get('from')  
    endorse_type = request.json.get('endorse_type')

    from_id = cache.get_account_id(ACCOUNT_PREFIX + _from)

    if endorse_type not in valid_assets:
      return jsonify({'error':'invalid_endorsement'})

    p = rpc.db_get_account_balances(from_id, [endorse_type])
    if p[0]['amount'] == 0:
      return jsonify({'error':'no_endorsement_available'})

    if from_id not in rpc.db_get_accounts([PROPUESTA_PAR_ID])[0]['blacklisted_accounts']:
      return jsonify({'error':'no_endore_state'})

    p = rpc.db_get_account_balances(from_id, [DESCUBIERTO_ID])
    if p[0]['amount'] > 0:
      return jsonify({'error':'already_have_credit'})

    asset, asset_core = rpc.db_get_assets([endorse_type, CORE_ASSET])
    
    memo = {
      'message' : '~ae'.encode('hex')
    }

    endorse_transfer_op = transfer(
      from_id,
      PROPUESTA_PAR_ID,
      asset,
      1,
      memo,
      None,
      CORE_ASSET
    )[0]

    print( "************************************************")
    print (json.dumps(endorse_transfer_op, indent=2))
    print ("*********************")

    # fees = rpc.db_get_required_fees([endorse_transfer_op], CORE_ASSET)
    print ("toma => ", endorse_transfer_op[1]['fee']['amount'])
    print ("************************************************")

    tx = build_tx_and_broadcast(
      account_whitelist(
        PROPUESTA_PAR_ID,
        from_id,
        0 #remove from black list
      ) + transfer(
        PROPUESTA_PAR_ID,
        from_id,
        asset_core,
        amount_value(endorse_transfer_op[1]['fee']['amount'], asset_core)
      ) + [endorse_transfer_op] + account_whitelist(
        PROPUESTA_PAR_ID,
        from_id,
        2 #add to black list
      )
    , None)

    to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)
    signature = bts2helper_sign_compact(to_sign, REGISTER_PRIVKEY)
    
    tx['signatures'] = [signature]
    return jsonify( {'tx':tx} )

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
      print( json.dumps(p, indent=2))
      return jsonify({'ok':'ok', 'coco':p})

    except Exception as e:
      logging.error(traceback.format_exc())
      return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)
  
  @app.errorhandler(404)
  def not_found(error):
    return make_response(jsonify({'error': 'not_found'}), 404)
  
  app.run(host="127.0.0.1", port=int(os.environ.get("PORT",8080)))
