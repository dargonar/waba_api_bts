import os

import websocket
import thread
import time

import requests
import json
import rpc
import cache

from time import sleep
from utils import *
from models import *

WS_NODE  = os.environ.get('UW_WS_NODE', 'ws://localhost:8090/')

def run_again():
  
  ws = websocket.WebSocketApp("ws://localhost:8090/",
    on_message = on_message,
    on_error = on_error,
    on_close = on_close
  )

  ws.on_open = on_open
  ws.run_forever()  

from random import uniform
from time import sleep

def on_message(ws, message):
  m = json.loads(message)
  if not ( 'method' in m and m['method'] == 'notice' and m['params'][0] == 1 ):
    return

  try:
    rpc.get_block()    

  except Exception as ex:
    print ex

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
  run_again()