from datetime import datetime
from dateutil.relativedelta import relativedelta

def calc_expiration(now, seconds):
  return now+relativedelta(seconds=seconds)

def build_tx(ops, ref_block_num, ref_block_prefix, expiration=120):
  return  {
    'expiration'        : calc_expiration(datetime.utcnow(), expiration).strftime('%Y%m%dT%H%M%S'),
    'ref_block_num'     : ref_block_num,
    'ref_block_prefix'  : ref_block_prefix,
    'operations'        : ops
  }

def register_account_op(registrar, referrer, referrer_percent, name, owner, active, memo, voting_account, fee=None):
  tmp = [
    5,
    {
      'registrar'         : registrar,
      'referrer'          : referrer,
      'referrer_percent'  : referrer_percent,
      'name'              : name,
      'owner' : {
        'weight_threshold' : 1,
        'account_auths'    : [],
        'key_auths'        : [[owner, 1]], 
        'address_auths'    : []
      },
      'active' : {
        'weight_threshold' : 1,
        'account_auths'    : [],
        'key_auths'        : [[active, 1]], 
        'address_auths'    : []
      },
      'options' : {
        'memo_key'       : active,
        'voting_account' : voting_account
      }
    }
  ]

  if fee : tmp[1]['fee']  = fee

  return tmp

def transfer_op(_from, _to, amount, memo=None, fee=None):
  tmp = [
    0,
    {
      "from"   : _from,
      "to"     : _to,
      "amount" : amount,
    }
  ]

  if fee : tmp[1]['fee']  = fee
  if memo: tmp[1]['memo'] = memo

  return tmp
