import os
import sys
import logging
import traceback
from datetime import datetime
from decimal import Decimal

from flask import Flask, jsonify, make_response, request
from flask_graphql import GraphQLView
from flask_cors import CORS, cross_origin

from schema import theSchema
from utils import *

from models import *
Base.metadata.create_all(get_engine())

from datatables import ColumnDT, DataTables

from ops import *
from bts2helper import *
import simplejson as json
from graphql.execution.executors.gevent import GeventExecutor
#from graphql.execution.executors.thread import ThreadExecutor

#ACCOUNT_PREFIX = '' 
from memcache import Client
import rpc

ERR_UNKNWON_ERROR    = 'unknown_error'

def create_app(**kwargs):
  app = Flask(__name__)
  app.debug = True
  app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=theSchema, **kwargs))

  @app.before_request
  def log_request():
    print request.data

  CORS(app)
    
  return app

if __name__ == '__main__':
  app = create_app(executor=GeventExecutor(), graphiql=True)

  @app.route('/api/v1/transfer', methods=['POST'])
  def transfer():
    try:
      req = request.json

      def build_amount( a ):
        if not a: return None
        return { "amount": int(Decimal(a)*ASSET_PRECISION), "asset_id" : ASSET_ID }
      
      print req.get('from')
      _from  = rpc.db_get_account_by_name( ACCOUNT_PREFIX + req.get('from') )['id']
      to     = req.get('to')
      amount = build_amount ( req.get('amount') )
      memo   = req.get('memo')

      top = transfer_op(_from, to, amount, memo)
      top[1]['fee'] = rpc.db_get_required_fees([top], ASSET_ID)[0]
      
      ref_block_num, ref_block_prefix = ref_block(rpc.db_get_dynamic_global_properties()['head_block_id'])
      tx = build_tx([top], ref_block_num, ref_block_prefix)
      to_sign = bts2helper_tx_digest(json.dumps(tx), CHAIN_ID)

      return jsonify( {'tx':tx, 'to_sign':to_sign} )
      
    except Exception as e:
      logging.error(traceback.format_exc())
      return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)

  # ############################################    
  # Backend api 
  # ############################################
  @app.route('/backend/dt/holding', methods=['GET'])
  def holding():
    
    columns = []
    columns.append(ColumnDT('id'))
    columns.append(ColumnDT('name'))
    #columns.append(ColumnDT('address.description')) # where address is an SQLAlchemy Relation
    #columns.append(ColumnDT('created_at', filter=str))

    # defining the initial query depending on your purpose
    query = DBSession.query(AccountBalance) #.join(Address).filter(Address.id > 14)

    # instantiating a DataTable for the query and table needed
    rowTable = DataTables(request.args, AccountBalance, query, columns)

    # returns what is needed by DataTable
    return jsonify( rowTable.output_result() )

  @app.route('/api/v1/push_id', methods=['POST'])
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

  @app.route('/api/v1/push_tx', methods=['POST'])
  def push_tx():
    tx  = request.json.get('tx')
    print tx
    return jsonify( rpc.network_broadcast_transaction(tx) )

  @app.route('/api/v1/get_global_properties', methods=['GET'])
  def db_get_global_properties():
    return jsonify( rpc.db_get_global_properties() )

  @app.route('/api/v1/get_dynamic_global_properties', methods=['GET'])
  def db_get_dynamic_global_properties():
    return jsonify( rpc.db_get_dynamic_global_properties() )

  @app.route('/api/v1/get_assets', methods=['POST'])
  def db_get_assets():
    return jsonify( rpc.db_get_assets(request.json) )

  @app.route('/api/v1/find_account', methods=['POST'])
  def find_account():
    key  = request.json.get('key')
    account_ids = set(rpc.db_get_key_references([key])[0])
    return jsonify([real_name(a['name']) for a in rpc.db_get_accounts(list(account_ids))])

  @app.route('/api/v1/account/<account>', methods=['GET'])
  def get_account(account):
    return jsonify( rpc.db_get_account_by_name(ACCOUNT_PREFIX+account) )
  
  @app.route('/api/v1/searchAccount', methods=['GET'])
  def search_account():
    search = request.args.get('search', '')
    
    res = []
    for tmp in rpc.db_lookup_accounts(ACCOUNT_PREFIX + search, 10):
      if tmp[0].startswith(ACCOUNT_PREFIX):
        tmp[0] = tmp[0][len(ACCOUNT_PREFIX):]

        print tmp[0], search
        if tmp[0].startswith(search):
          res.append( tmp )
    return jsonify( res )

  @app.route('/api/v1/register', methods=['POST'])
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
        BSW_REGISTER_ACCOUNT, 
        BSW_REGISTER_ACCOUNT, 
        0, 
        name, 
        owner, 
        active, 
        memo, 
        BSW_REGISTER_ACCOUNT,
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
      p = rpc.network_broadcast_transaction(tx)
      return jsonify({'ok':'ok', 'coco':p})

    except Exception as e:
      logging.error(traceback.format_exc())
      return make_response(jsonify({'error': ERR_UNKNWON_ERROR}), 500)
  
  @app.errorhandler(404)
  def not_found(error):
    return make_response(jsonify({'error': 'not_found'}), 404)
  
  app.run(host="0.0.0.0", port=os.environ.get("PORT",8080))
