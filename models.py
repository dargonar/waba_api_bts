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
  return create_engine(strconn, echo=False, poolclass=NullPool)

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
