# -*- mode: python; coding: utf-8 -*-
"""Abstraction for sqlalchemy vs django engines.
"""

# It may be better/easier to just use django in place of sqlalchemy. TBD.

import os
from types import MethodType
import atexit

import django.db.models
import sqlalchemy.types
import sqlalchemy.ext.declarative

from coincharts import config

# We're replacing the module with a dict. Importing the file shouldn't result in reading from disk, etc. That's why.
config = config.get_config()

datetime_field = 'time_period_end'
price_field = 'price_close'

schema = [
    ('time_period_start', 'TEXT'),
    ('time_period_end', 'TEXT'),
    ('time_open', 'TEXT'),
    ('time_close', 'TEXT'),
    ('price_open', 'REAL'),
    ('price_high', 'REAL'),
    ('price_low', 'REAL'),
    ('price_close', 'REAL'),
    ('volume_traded', 'REAL'),
    ('trades_count', 'INTEGER'),
]

type_mappings = {
    'django': {
        'TEXT': django.db.models.CharField,
        'REAL': django.db.models.FloatField,
        'INTEGER': django.db.models.IntegerField,
    },
    
    'sqlalchemy': {
        'TEXT': sqlalchemy.types.String,
        'INTEGER': sqlalchemy.types.Integer,
        'REAL': sqlalchemy.types.Float,
    },
}

# to-be-bound to classes created below
def __str__(self):
    class_name = self.__class__.__name__
    return '<{}({}@{})>'.format(
        class_name,
        getattr(self, TIME),
        getattr(self, PRICE),
    )
Base = None

def get_db_table(symbol_id, orm):
    global Base
    mapping = type_mappings[orm]
    columns = {}
    for name, type_ in schema:
        type_ = mapping[type_]
        if orm == 'django':
            columns[name] = type_()
        elif orm == 'sqlalchemy':
            columns[name] = sqlalchemy.Column(type_)
        else:
            raise Exception('Unknown ORM "{}"'.format(orm))

    if orm == 'django':
        klass = type(symbol_id, (models.Model,), columns)
        klass.__str__ = __str__
    elif orm == 'sqlalchemy':
        Base = sqlalchemy.ext.declarative.declarative_base()
        columns['__tablename__'] = symbol_id.lower()
        columns['id'] = sqlalchemy.Column(sqlalchemy.types.Integer, primary_key=True)
        klass = type(symbol_id, (Base,), columns)
        klass.__repr__ = __str__
    else:
        raise Exception('fixme: tooooo complicated')
    
    return klass


def get_sqlalchemy_session(db_path, echo=False):
    """Create and return a SQLAlchemy `session` object
    """
    db_path = os.path.abspath(db_path)
    engine = sqlalchemy.create_engine('sqlite:///{db_path}'.format(db_path=db_path), echo=echo)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)
    atexit.register(session.close)
    return session


"""
class Page(models.Model):
    weight = models.FloatField(default=0.0)
    name = models.CharField(max_length=30)
    label = models.CharField(max_length=60)
    headline = models.CharField(max_length=200)
    tab_visible = models.BooleanField('Should tab be visible?', default=True)

    def __str__(self):
        return self.name

class Content(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    main = models.TextField(blank=True)
    rhs = models.TextField(blank=True)

    def __str__(self):
        return self.page.name
"""


"""
from sqlalchemy import Column, Integer, String
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    password = Column(String)

    def __repr__(self):
       return "<User(name='%s', fullname='%s', password='%s')>" % (
                            self.name, self.fullname, self.password)
"""
