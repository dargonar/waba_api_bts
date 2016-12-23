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

from models import *
Base.metadata.create_all(get_engine())

from bts2helper import *

WS_NODE  = os.environ.get('UW_WS_NODE', 'ws://localhost:8090/')

def run_again():
  
  ws = websocket.WebSocketApp("ws://localhost:8090/",
    on_message = on_message,
    on_error = on_error,
    on_close = on_close
  )

  ws.on_open = on_open
  ws.run_forever()  

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

  a1, is_new = get_or_create(db, AccountBalance, account_id=transfer.to_id, asset_id=ASSET_ID)
  a1.amount += amount['amount']
  a1.account_name = transfer.to_name

  a2, is_new = get_or_create(db, AccountBalance, account_id=transfer.from_id, asset_id=ASSET_ID)
  a2.amount -= amount['amount']
  if transfer.fee_asset == ASSET_ID:
    a2.amount -= fee['amount']
  a2.account_name = transfer.from_name

  return transfer, a1, a2
  

def on_message(ws, message):
  m = json.loads(message)
  if not ( 'method' in m and m['method'] == 'notice' and m['params'][0] == 1 ):
    return

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
                t,a1,a2 = transfer_from_op(op, next_block['timestamp'], new_block.id, from_block+blk_inx, trx_in_block, op_in_trx)
                db.add(t)
                db.merge(a1)
                db.merge(a2)
         
          db.commit()
          my_block = new_block

  except Exception as ex:
    print ex
    logging.error(traceback.format_exc())

def on_error(ws, error):
  print error

def on_close(ws):
  print "### closed ###"
  sleep(5)
  run_again()

def on_open(ws):
  ws.send(
    json.dumps( {"id":1, "method":"call", "params":[0, "set_block_applied_callback", [1]]} )
  )

if __name__ == "__main__":
  
  holders = rpc.db_get_asset_holders(ASSET_ID)
  with session_scope() as db:
    for h in holders:
      acc, is_new = get_or_create(db, AccountBalance, account_id=h['account_id'], asset_id=ASSET_ID)
      acc.account_name = h['name']
      acc.amount       = h['amount']
      db.add(acc)
    db.commit()
    
  run_again()