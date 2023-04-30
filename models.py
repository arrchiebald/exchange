from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, BigInteger, Text
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
Session = sessionmaker()

class Users(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True)
    username = Column(String(32), nullable=False)
    first_name = Column(String(64))
    last_name = Column(String(64))

class UserHistory(Base):
    __tablename__ = 'user_history'

    id = Column(BigInteger, primary_key=True)
    last_trc20_wallet = Column(String(100))
    last_request_uah = Column(String(100))
    last_card = Column(String(100))
    last_request_usdt = Column(String(100))
    last_bank = Column(String(100))

class ApplicationsSell(Base):
    __tablename__ = 'applications_sell'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger)
    bank = Column(String(32))
    usdt_rate = Column(Float)
    wallet = Column(String(62))
    uah_amount = Column(Float)
    usdt_amount = Column(Float)
    data_created = Column(String(20))
    time_created = Column(String(20))
    status = Column(String(30))

class ApplicationsBuy(Base):
    __tablename__ = 'applications_buy'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer)
    txid = Column(Text)
    bank = Column(String(32))
    usdt_rate = Column(Float)
    credit_card = Column(BigInteger)
    usdt_amount = Column(Float)
    uah_summa = Column(Float)
    data_created = Column(String(20))
    time_created = Column(String(20))
    status = Column(String(30))
