import unicodedata
from memcache import Client
import simplejson as json
from models import *
import init_model

mc = Client(["127.0.0.1:11211"], debug=1)

def get_configuration():
  key = 'dsc_configuration'
  dsc = mc.get(key)
  if not dsc:
    with session_scope() as db:
      #ret = db.query(NameValue).filter(NameValue.name=='configuration').first()
      nm, is_new = get_or_create(db, NameValue, name  = 'configuration')
      if is_new:
        nm.value = init_model.get_default_configuration()
        nm.updated_at = datetime.utcnow()
        db.add(nm)
        db.commit()  
      dsc = {'value': nm.value, 'updated_at': nm.updated_at}
    mc.set(key, dsc, 60)
  return dsc