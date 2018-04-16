import os
import logging
from decimal import Decimal
from datetime import datetime
from contextlib import contextmanager
from collections import OrderedDict

from sqlalchemy import create_engine, UniqueConstraint, func
from sqlalchemy import or_, and_
from sqlalchemy import MetaData, Column, Table, ForeignKey, TypeDecorator
from sqlalchemy import BigInteger, Integer, String, DateTime, Enum, Boolean, Date, Numeric, Text, Unicode, UnicodeText
from sqlalchemy.types import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, scoped_session, sessionmaker
from sqlalchemy.sql import select
from sqlalchemy.pool import NullPool

from utils import *

class CoerceToInt(TypeDecorator):
  impl = Integer
  def process_result_value(self, value, dialect):
    
    if value is not None:
      value = int(value)
    else:
      value = 0

    return value

naming_convention = {
  "ix": 'ix_%(column_0_label)s',
  "uq": "uq_%(table_name)s_%(column_0_name)s",
  "ck": "ck_%(table_name)s_%(constraint_name)s",
  "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s"
}

def get_engine():
  strconn = DB_URL
  return create_engine(strconn, echo=False, poolclass=NullPool, encoding='utf8')

def get_metadata():
  return MetaData(bind=get_engine(), naming_convention=naming_convention)

def get_session():
  return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=get_engine()))

@contextmanager
def session_scope():
  """Provide a transactional scope around a series of operations."""
  session = get_session()
  try:
      yield session
      session.commit()
  except:
      session.rollback()
      raise
  finally:
      session.close()

Base = declarative_base(metadata=get_metadata())

def get_or_create(session, model, **kwargs):
  instance = session.query(model).filter_by(**kwargs).first()
  if instance:
    return instance, False
  else:
    instance = model(**kwargs)
    session.add(instance)
    return instance, True

class TimestampMixin(object):
  created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

  def older_than(self, delta):
    return datetime.utcnow() - self.created_at > delta

class PushInfo(Base, TimestampMixin):
  __tablename__ = 'push_info'
  
  id      = Column(Integer, primary_key=True)
  name    = Column(String(128), unique=True)
  push_id = Column(String(256))

class Block(Base, TimestampMixin):
  __tablename__ = 'block'
  
  id         = Column(Integer, primary_key=True)
  block_id   = Column(String(256), unique=True)
  block_num  = Column(Integer, unique=True)

class AccountBalance(Base, TimestampMixin):
  __tablename__ = 'account_balance'
  
  id            = Column(Integer, primary_key=True)
  account_id    = Column(String(32))
  account_name  = Column(String(63))
  asset_id      = Column(String(32))
  amount        = Column(BigInteger, default=0)

  def to_dict(self):
    return {
      'id'     : self.account_id,
      'name'   : real_name(self.account_name),
      'amount' : amount_value(self.amount,{'precision':4})
    }

class UserData(Base, TimestampMixin):
  __tablename__ = 'user_data'
  
  id             = Column(Integer, primary_key=True)
  wallet_name    = Column(String(64))

  name           = Column(String(64))
  category       = Column(String(64))
  address        = Column(String(64))
  lat            = Column(String(64))
  lon            = Column(String(64))
  emp_web        = Column(String(64))
  contacto_email = Column(String(64))
  contacto_tel   = Column(String(64))


class Transfer(Base, TimestampMixin):
  __tablename__ = 'transfer'
  
  block_id     = Column(Integer, ForeignKey("block.id", ondelete="CASCADE"), nullable=False) 
  
  id           = Column(Integer, primary_key=True)
  
  from_id      = Column(String(32))
  from_name    = Column(String(63))
  
  to_id        = Column(String(32))
  to_name      = Column(String(63))

  amount       = Column(BigInteger)
  amount_asset = Column(String(32))
 
  fee          = Column(Integer)
  fee_asset    = Column(String(32))

  timestamp    = Column(DateTime)
  
  block_num    = Column(Integer)
  trx_in_block = Column(Integer)
  op_in_trx    = Column(Integer)
  
  memo         = Column(String(32))

  processed    = Column(Integer, default=0, index=True)

class LastError(Base, TimestampMixin):
  __tablename__ = 'last_error'

  id           = Column(Integer, primary_key=True)
  transfer_id  = Column(Integer, ForeignKey("transfer.id", ondelete="CASCADE"), nullable=False, unique=True) 
  description  = Column(Text)
  
  txid         = Column(String(64), index=True)
  
  block_num    = Column(Integer)
  trx_in_block = Column(Integer)

class NameValue(Base, TimestampMixin):
  __tablename__ = 'name_value'
  id           = Column(Integer, primary_key=True)
  name         = Column(String(256), index=True)
  value        = Column(JSON)
  
class Category(Base, TimestampMixin):
  __tablename__ = 'category'
  id           = Column(Integer, primary_key=True)
  name         = Column(String(256), index=True)
  description  = Column(String(256), index=True)
  parent_id    = Column(Integer, index=True)
  
  def to_dict(self):
    return {
      'id'          : self.id,
      'name'        : self.name,
      'description' : self.description,
      'parent_id'   : self.parent_id
    }

class Business(Base, TimestampMixin):
  __tablename__     = 'business'
  id                = Column(Integer, primary_key=True)
  name              = Column(String(256), index=True)
  description       = Column(String(256))
  account           = Column(String(256), index=True)
  account_id        = Column(String(32), index=True)
#   category_id       = Column(Integer, index=True)
  category_id       = Column(Integer, ForeignKey("category.id"))
#   subcategory_id    = Column(Integer, index=True)
  subcategory_id    = Column(Integer, ForeignKey("category.id"))
  balance           = Column(BigInteger, default=0)
  total_refunded    = Column(BigInteger, default=0)
  total_discounted  = Column(BigInteger, default=0)
  initial_credit    = Column(BigInteger, default=0)
  discount          = Column(Numeric(5,2), index=True)
  image             = Column(String(256))
  location          = Column(String(256))
  latitude          = Column(Numeric(10,8), index=True)
  longitude         = Column(Numeric(11,8), index=True)
  address           = Column(String(256))
  
  category = relationship('Category', foreign_keys=category_id)
  subcategory = relationship('Category', foreign_keys=subcategory_id)
  discount_schedule = relationship("DiscountSchedule", back_populates="business")
  
#   billing_address_id = Column(Integer, ForeignKey("address.id"))
#   billing_address = relationship("Address", foreign_keys=[billing_address_id])
    
  def to_dict(self, get_balances=False):
    if get_balances:
      p = rpc.db_get_account_balances(self.account_id, [DISCOIN_ID, DISCOIN_CREDIT_ID, DISCOIN_ACCESS_ID])
    return {
        'id'              : self.id,
        'name'            : self.name,
        'description'     : self.description,
        'account'         : self.account,
        'account_id'      : self.account_id,
        'category_id'     : self.category_id,
        'subcategory_id'  : self.subcategory_id,
        'balance'         : self.balance,
        'initial_credit'  : self.initial_credit,
        'balances'        : p if get_balances else {},
        'total_refunded'  : self.total_refunded,
        'total_discounted': self.total_discounted,
        
        'discount' : self.discount,
        'image' : self.image,
        'location' : self.location,
        'latitude' : self.latitude,
        'longitude' : self.longitude,
        'address' : self.address,
        'category' : self.category.to_dict() if self.category else None,
        'subcategory' : self.subcategory.to_dict() if self.subcategory else None,
        'discount_schedule' : [x.to_dict() for x in self.discount_schedule] if self.discount_schedule else []
    }
  
  def from_dict(self, dict):
    self.name = dict['name']
    self.description  = dict['description']
    self.account  = dict['account']
    self.account_id = dict['account_id']
    self.category_id  = dict['category_id']
    self.subcategory_id = dict['subcategory_id']
    self.balance  = dict['balance']
    self.total_refunded = dict['total_refunded']
    self.total_discounted = dict['total_discounted']
    self.initial_credit = dict['initial_credit']
    self.discount = dict['discount']
    self.image  = dict['image']
    self.location = dict['location']
    self.latitude = dict['latitude']
    self.longitude  = dict['longitude']
    self.address  = dict['address']
    
  
class DiscountSchedule(Base, TimestampMixin):
  __tablename__     = 'discount_schedule'
  id                = Column(Integer, primary_key=True)
#   business_id       = Column(Integer, index=True)
  business_id       = Column(Integer, ForeignKey('business.id'))
  date              = Column(String(32), index=True)
  discount          = Column(Numeric(5,2), index=True)
  
  business          = relationship("Business", back_populates="discount_schedule")
    
  def to_dict(self):
    return {
      'id' : self.id,
      'business_id' : self.business_id,
      'date' : self.date,
      'discount' : self.discount
    }
