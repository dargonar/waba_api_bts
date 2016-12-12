import graphene

import rpc
import cache

from decimal import Decimal
from utils import *


# class AuthorizationMiddleware(object):
#   def resolve(self, next, root, args, context, info):

#     if info.field_name == 'user':
#         return None
#     return next(root, args, context, info)

class Amount(graphene.ObjectType):
  quantity = graphene.String()
  asset    = graphene.Field(lambda:Asset)

class Asset(graphene.ObjectType):
  id     = graphene.String()
  symbol = graphene.String()
  issuer = graphene.Field(lambda:Account)

  def __init__(self, asset):
    self.asset = asset

  def resolve_id(self, args, context, info):
    return self.asset['id']

  def resolve_symbol(self, args, context, info):
    print 'resolviendo simbolo'
    return self.asset['symbol']

  #@graphene.with_context
  def resolve_issuer(self, args, context, info):
    return Account( cache.get_account(self.asset['issuer']) )

class Memo(graphene.ObjectType):
  from_   = graphene.String(name='from')
  to      = graphene.String()
  nonce   = graphene.String()
  message = graphene.String()

class Block(graphene.ObjectType):
  previous                = graphene.String()
  timestamp               = graphene.String()
  witness                 = graphene.String()
  transaction_merkle_root = graphene.String()
  extensions              = graphene.String()
  witness_signature       = graphene.String()
  block_id                = graphene.String()
  signing_key             = graphene.String()

class Operation(graphene.Interface):
  id        = graphene.String()
  fee       = graphene.Field(Amount)
  block     = graphene.Field(Block)

  def resolve_id(self, args, context, info):
    return self.op['info']['id']

  #@graphene.with_context
  def resolve_block(self, args, context, info):
    block = cache.get_block_header(self.op['info']['block_num'])
    return Block(
      previous                = block['previous'],
      timestamp               = block['timestamp'],
      witness                 = block['witness'],
      transaction_merkle_root = block['transaction_merkle_root'],
      extensions              = block['extensions'],
      #witness_signature       = block['witness_signature'],
      #block_id                = block['block_id'],
      #signing_key             = block['signing_key'],
    )

  #@graphene.with_context
  def resolve_fee(self, args, context, info):
    asset = cache.get_asset(self.op['fee']['asset_id'])
    return Amount(
      quantity = amount_value( str(self.op['fee']['amount']), asset),
      asset    = Asset(asset)
    )


class NoDetailOp(graphene.ObjectType):
  name = graphene.String()

  def __init__(self, op):
    self.op = op

  class Meta:
    interfaces = (Operation, )

class Transfer(graphene.ObjectType):
  from_       = graphene.Field(lambda:Account, name='from')
  to          = graphene.Field(lambda:Account)
  amount      = graphene.Field(Amount)
  memo        = graphene.Field(Memo)
  type_       = graphene.String(name='type')

  def __init__(self, op):
    self.op = op

  class Meta:
    interfaces = (Operation, )

  #@graphene.with_context
  def resolve_from_(self, args, context, info):
    return Account( cache.get_account(self.op['from']) )

  #@graphene.with_context
  def resolve_to(self, args, context, info):
    return Account( cache.get_account(self.op['to']) )

  #@graphene.with_context
  def resolve_amount(self, args, context, info):
    print '[START] get_asset'
    asset = cache.get_asset(self.op['amount']['asset_id'])
    print '[END] get_asset'
    return Amount(
      quantity = amount_value( str(self.op['amount']['amount']), asset),
      asset    = Asset(asset)
    )


  #@graphene.with_context
  def resolve_memo(self, args, context, info):
    if not 'memo' in self.op: return None
    return Memo(
      from_   = self.op['memo']['from'],
      to      = self.op['memo']['to'],
      nonce   = self.op['memo']['nonce'],
      message = self.op['memo']['message']
    )

  #@graphene.with_context
  def resolve_type_(self, args, context, info):
    f = cache.get_account(self.op['from'])['name']

    #HACK:
    x = info.operation.selection_set.selections[0].arguments[0].value.value
    if x == f: return 'sent'
    return 'received'

#@Schema.register
class Account(graphene.ObjectType):

  name    = graphene.String()
  history = graphene.List(Operation,
   start = graphene.Int(),
   limit = graphene.Int()
  )
  
  #history = graphene.List(Operation)
  
  balance = graphene.List(Amount)

  def __init__(self, account):
    self.account = account

  #@graphene.with_context
  def resolve_name(self, args, context, info):
    name = self.account['name']
    return real_name(name)
  
  #@graphene.with_context
  def resolve_balance(self, args, context, info):
    bals = rpc.db_get_account_balances(self.account['id'])

    # print '******************'
    # print bals

    res = []
    for b in bals:
      asset = cache.get_asset(b['asset_id'])
      res.append(Amount(
        quantity = amount_value( str(b['amount']), asset),
        asset    = Asset(asset)
      ))
    return res

  #@graphene.with_context
  def resolve_history(self, args, context, info):

    start   = int(args.get('start', 0))
    limit   = int(args.get('limit', 10))

    print '[START] ws.history_get_relative_account_history '
    ops = rpc.history_get_relative_account_history(self.account['id'], 0, limit, start)
    print '[START] ws.history_get_relative_account_history '

    history = []

    for tmp in ops:
      op = tmp['op']
      
      op[1]['info'] = tmp

      if op[0] == 0:
        history.append(Transfer(op[1]))
      else:
        history.append(NoDetailOp(op[1]))

    return history

class Query(graphene.ObjectType):
  account = graphene.Field(Account, 
    name = graphene.String()
  )

  #@graphene.with_context
  def resolve_account(self, args, context, info):
    account_name = args.get('name')
    if not account_name: raise

    account_id = cache.get_account_id(TEST_PESOCIAL + account_name)
    return Account(cache.get_account(account_id))


theSchema = graphene.Schema(query=Query, types=[NoDetailOp, Transfer])
print theSchema
