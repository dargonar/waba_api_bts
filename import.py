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
Base.metadata.create_all(get_engine())

from bts2helper import *

WS_NODE  = os.environ.get('UW_WS_NODE', 'ws://localhost:8090/')

def get_my_last_block(db):
  q = db.query(Block)
  q = q.order_by(Block.block_num.desc())
  return q.first()

def undo_block(db, block):
  # Remove block from main chain
  db.query(Block).filter(Block.id == block.id).delete()
  db.flush()
 
  # Get previous
  return get_my_last_block(db)

def transfer_from_op(op, ts, new_block_id, block_num, trx_in_block, op_in_trx):

  print op
  
  to_id   = op[1]['to']
  from_id = op[1]['from']
  amount  = op[1]['amount']
  fee     = op[1]['fee']
  
  amount_asset = cache.get_asset(amount['asset_id'])
  fee_asset    = cache.get_asset(fee['asset_id'])

  transfer = Transfer(
    block_id     = new_block_id,
    from_id      = from_id,
    from_name    = cache.get_account(from_id)['name'],
    to_id        = to_id,
    to_name      = cache.get_account(to_id)['name'],
    amount       = amount['amount'],
    amount_asset = amount['asset_id'],
    fee          = fee['amount'],
    fee_asset    = fee['asset_id'],
    block_num    = block_num,
    trx_in_block = trx_in_block,
    op_in_trx    = op_in_trx,
    timestamp    = parse(ts)
  )
  
  return transfer
  

def do_import():
  try:
    with session_scope() as db:
      # My last block imported in DB
      my_block = get_my_last_block(db)

      # Network last block (head of master chain)
      dgp = rpc.db_get_dynamic_global_properties()
      #print dgp
      
      # Check participation rate
      pr = rpc.calc_participation_rate(int(dgp['recent_slots_filled']))
      if int(pr) < 75:
        print 'Participation rate too low'
        return
      
      last_block_num = dgp['head_block_number']
      
      run_update_holders = False
      while last_block_num > my_block.block_num:
        
        from_block = int(my_block.block_num+1)
        print from_block
        
        next_block = rpc.db_get_block_header(from_block)
        
        if next_block['previous'] != my_block.block_id:
          my_block = undo_block(db, my_block)
        else:
          
          to_block = min(from_block+5000, last_block_num)
          
          blocks = rpc.db_get_blocks(from_block, to_block)
                    
          new_block = Block(
            block_num  = to_block,
            block_id   = bts2helper_block_id(json.dumps(blocks[-1]))
          )

          db.add(new_block)
          db.flush()
          
          for blk_inx, next_block in enumerate(blocks):
            for trx_in_block, tx in enumerate(next_block['transactions']):
              for op_in_trx, op in enumerate(tx['operations']):
                if not ( op[0] == 0 and op[1]['amount']['asset_id'] == ASSET_ID ):
                  continue
                t = transfer_from_op(op, next_block['timestamp'], new_block.id, from_block+blk_inx, trx_in_block, op_in_trx)
                db.add(t)
                run_update_holders = True
         
          db.commit()
          my_block = new_block
      
      if run_update_holders:
        update_holders(db)
        db.commit()

  except Exception as ex:
    print ex
    logging.error(traceback.format_exc())

  
if __name__ == "__main__":

  with session_scope() as db:
    update_holders(db)
    db.commit()
  
  while True:
    try:
      do_import()
      sleep(3)
    except Exception as ex:
      logging.error(traceback.format_exc())