from datetime import datetime
import random
from sqlalchemy import (
    Column,
    Boolean,
    Integer,
    Numeric,
    Text,
    String,
    ForeignKey,
    Table,
    )

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship)

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


#class MyModel(Base):
#    __tablename__ = 'models'
#    id = Column(Integer, primary_key=True)
#    name = Column(Text, unique=True)
#    value = Column(Integer)
#
#    def __init__(self, name, value):
#        self.name = name
#        self.value = value

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True)

bundles = Table('bundles', Base.metadata,
    Column('bundle', String(20), ForeignKey('products.sku'), primary_key=True),
    Column('product', String(20), ForeignKey('products.sku'), primary_key=True),
)

class Product(Base):
    __tablename__ = 'products'
    name = Column(Text)
    sku = Column(String(20), primary_key=True)
    price = Column(Numeric(precision=7, scale=2))
    bundle = Column(Boolean)
    items = relationship("Product", secondary=bundles,
        primaryjoin=sku==bundles.c.bundle,
        secondaryjoin=sku==bundles.c.product,
        backref="bundles"
    )
    maxsku = Column(Integer)
    hidden = Column(Boolean)
    display_order = Column(Integer)
    description = Column(Text)
    url = Column(String(2000))


class License():

    def check(self, regid, check_valid=False):
        """ Returns True if licence exists, if check_valid checks valid!=N
        """
        anlicenses = Table('anlicenses', Base.metadata, autoload=True)
        row = anlicenses.select().where(anlicenses.c.regid==regid).execute().fetchone()
        print row
        return row is not None and check_valid and row['valid'] != 'N'

    def generate(self):
        while True:
            regid = ''.join(random.choice("BCDFGHJKLMNPQRSTVWXZ") for _ in range(12))
            if not self.check(regid):
                return regid

    def create(self):
        order = Order()
        DBSession.add(order)
        DBSession.flush()
        print '================================================='
        pdidx = Table('pdidx', Base.metadata, autoload=True)
        ins = pdidx.insert().values(source='Website', orderid=order.order_id)
        result = ins.execute()
        DBSession.flush()
        anlicenses = Table('anlicenses', Base.metadata, autoload=True)
        regid = self.generate()
        print regid
        result = anlicenses.insert().values(
                pdserial=result.inserted_primary_key[0],
                regid=regid,
                sequence=1,
                created=datetime.now(),
                lastchange=datetime.now(),
                source='Website',
                orderid=order.order_id,
            ).execute()
        DBSession.flush()
        return regid




