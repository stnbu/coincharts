# -*- mode: python; coding: utf-8 -*-

from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def get_symbol_class(symbol_id):

    schema = [
        ('time_period_start', String),
        ('time_period_end', String),
        ('time_open', String),
        ('time_close', String),
        ('price_open', Float),
        ('price_high', Float),
        ('price_low', Float),
        ('price_close', Float),
        ('volume_traded', Float),
        ('trades_count', Integer),
    ]

    attrs = dict(
        __tablename__=symbol_id,
        id=Column(Integer, primary_key=True))

    for column, type_ in schema:
        attrs[column] = Column(type_)

    return type(symbol_id, (Base,), attrs)


if __name__ == '__main__':

    BTC = get_symbol_class('BITSTAMP_SPOT_BTC_USD')
    engine = create_engine('sqlite:////Users/mburr/git/crypto_dashboard_play/db_x.sqlite3', echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)

    btc = BTC(
        time_period_start='bob',
        time_period_end='frank',
        time_open='fdsa',
        time_close='fdsa',
        price_open=3.0,
        price_high=2.0,
        price_low=0.0,
        price_close=1.0,
        volume_traded=9.9,
        trades_count=9,
    )

    our_btc = session.query(BTC).filter_by(time_period_start='bob').first()

    print(btc is our_btc)
