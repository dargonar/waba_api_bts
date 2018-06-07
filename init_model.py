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

import simplejson as json

from memcache import Client
import rpc
import cache

def get_default_configuration():
  #return {  'warnings': {    'first':  { 'from_amount' : 0,  'to_amount' : 60,  'amount':0 , 'description' : 'Ok',      'color': '#52c41a',      'extra_percentage' : 0    }, 'second': { 'from_amount' : 60, 'to_amount' : 80,  'amount':60, 'description' : 'Cuidado',      'color': '#faad14', 'extra_percentage' : 5    } , 'third':  { 'from_amount' : 80, 'to_amount' : 100, 'amount':80, 'description' : '',      'color': '#f5222d',        'extra_percentage' : 10    }  },  'bootstrap':{    'referral':{      'reward'        : 25,      'max_referrals' : 10,      'max_supply'    : 0    },    'airdrop':{      'max_registered_users' : 10000,      'amount'               : 100,      'max_supply'           : 1000000    },    'transactions':{      'max_refund_by_tx' : 500,      'min_refund_by_tx' : 50,      'max_supply'       : 5000000    },    'refund':[      {        'from_tx' : 0,        'to_tx' : 10000,        'tx_amount_percent_refunded' : 25      },      {        'from_tx' : 10000,        'to_tx' : 50000,        'tx_amount_percent_refunded' : 15      },      {        'from_tx' : 50000,        'to_tx' : 100000,        'tx_amount_percent_refunded' : 10      }    ]  },  'issuing' : {    'new_member_percent_pool' : 10  }} 
  return {  "airdrop": {    "by_wallet": {      "first_wallet_download": 10000,      "reward_amount": 100, "first_tx_reward_amount": 100    },    "by_referral": {      "referred_max_quantity": 5,      "referred_amount": 25,      "referrer_amount": 25    },    "by_reimbursement": {      "first": {        "from_tx": 0,        "to_tx": 10000,        "tx_amount_percent_refunded": 25      },      "second": {        "from_tx": 10000,        "to_tx": 50000,        "tx_amount_percent_refunded": 15      },      "third":{        "from_tx": 50000,        "to_tx": 100000,        "tx_amount_percent_refunded": 10      }      }  },  "reserve_fund": {    "new_business_percent": 10  },  "warnings": {    "first": {      "amount": 0,      "color": "#52c41a",      "description": "Ok",      "extra_percentage": 0,      "from_amount": 0,      "to_amount": 60    },    "second": {      "amount": 60,      "color": "#faad14",      "description": "Cuidado",      "extra_percentage": 5,      "from_amount": 60,      "to_amount": 80    },    "third": {      "amount": 80,      "color": "#f5222d",      "description": "Danger",      "extra_percentage": 10,      "from_amount": 80,      "to_amount": 100    }  }}
def get_default_categories():
    return  {    'rows': [        {            'row' : 1,            'description': 'Menos de 200 mil'        },        {            'row' : 2,            'description': '200 mil - 500 mil'        },        {            'row' : 3,            'description': '500 mil - 750 mil'        }    ],    'cols': [        {            'col' : 1,            'refund_rate': 10        },        {            'col' : 2,            'refund_rate': 15        },        {            'col' : 3,            'refund_rate': 20        }    ],    'categories': [        {            'row' : 1,            'col' : 1,            'initial_credit' : 2000        },        {            'row' : '1',            'col' : '2',            'initial_credit' : 3000        },        {            'row' : '1',            'col' : '3',            'initial_credit' : 4000        }    ]}

def init_categories():
  cats = [ {'name':u'Gastronomía', 
            'subcats':['Restaurantes', 'Fast Food', u'Cervecerías', 'Bar', 'Otros']},
           {'name':'Indumentaria',
           'subcats':['Unisex', 'Mujer', 'Hombre', u'Bebes & niños', 'Calzado', 'Marroquineria', 'Otros']}]

  with session_scope() as db:
    if db.query(Category).first():
      return
    for cat in cats:
      print (' ================== Initilizing categories:')
      print (cat)
      category = Category()
      category.name        = cat['name']
      category.description = cat['name']
      category.parent_id   = None
      db.add(category)
      db.flush()
      db.refresh(category)
      for sub_cat in cat['subcats']:
        subcategory = Category()
        subcategory.name        = sub_cat
        subcategory.description = sub_cat
        subcategory.parent_id   = category.id
        db.add(subcategory)
    db.commit()

def init_businesses():
  bizs = [{ 'name' :            'Antares'
          , 'description' :     'Cerveceria Antares'
          , 'account' :         'discoin.biz1'
          , 'account_id' :      '1.2.21'
          , 'category_id' :     1
          , 'subcategory_id' :  4
          , 'balance' :         0
          , 'total_refunded' :  0
          , 'total_discounted' :0 
          , 'initial_credit' :  0
          , 'discount' :        Decimal(10)
          , 'image' :           ''
          , 'location' :        ''
          , 'latitude' :        Decimal(-34.919665) 
          , 'longitude' :       Decimal(-57.960685)
          , 'address' :         'Calle 22 n75, La Plata'},

          { 'name' :            'Mostaza'
          , 'description' :     'Hamburguesa zarpada'
          , 'account' :         'discoin.biz2'
          , 'account_id' :      '1.2.22'
          , 'category_id' :     1
          , 'subcategory_id' :  3
          , 'balance' :         0
          , 'total_refunded' :  0
          , 'total_discounted' :0 
          , 'initial_credit' :  0
          , 'discount' :        Decimal(20.5)
          , 'image' :           ''
          , 'location' :        ''
          , 'latitude' :        Decimal(-34.919665) 
          , 'longitude' :       Decimal(-57.960685)
          , 'address' :         'Calle 22 n75, La Plata'}
        ]
  

  with session_scope() as db:
    if db.query(Business).first():
      return
    for biz in bizs:
      business = Business()
      business.from_dict(biz)
      business.category_id    = db.query(Category).filter(Category.parent_id==None).first().id
      business.subcategory_id = db.query(Category).filter(Category.parent_id==business.category_id).first().id
      db.add(business)
    db.commit()

def init_discount_schedule():
  
  discounts = [{
                'date' : 'monday', 
                'discount': Decimal(20)
              },
              {
                'date' : 'tuesday', 
                'discount': Decimal(20)
              },
              {
                'date' : 'wednesday', 
                'discount': Decimal(20)
              },
              {
                'date' : 'thursday', 
                'discount': Decimal(20)
              },
              {
                'date' : 'friday', 
                'discount': Decimal(20)
              },
              {
                'date' : 'saturday', 
                'discount': Decimal(20)
              },
              {
                'date' : 'sunday', 
                'discount': Decimal(20)
              }]

  with session_scope() as db:
    if db.query(DiscountSchedule).first():
      return
    for biz in db.query(Business).all():
      for discount in discounts:
        dis = DiscountSchedule()
        dis.date        = discount['date']
        dis.discount    = discount['discount']
        dis.business_id = biz.id
        db.add(dis)
    db.commit()
