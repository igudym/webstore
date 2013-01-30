from datetime import datetime
import random
from sqlalchemy import (
    Column,
    Boolean,
    Integer,
    Numeric,
    DateTime,
    Text,
    String,
    ForeignKey,
    Table,
    )

from sqlalchemy.orm import relationship

from dbsession import DBSession, Base

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(100))
    items = relationship("Items")
    pdserial = Column(Integer)
    total = Column(Numeric(precision=7, scale=2))
    payment = Column(String(20))
    status = Column(String(20))
    created = Column(DateTime)
    addr1 = Column(String(100))
    addr2 = Column(String(100))
    city = Column(String(100))
    state = Column(String(100))
    zipcode = Column(String(100))
    country = Column(String(100))

    @staticmethod
    def confirm(order_id):
        order = DBSession.query(Order).filter(order_id==order_id).one()
        order.status = 'paid'
        if order.pdserial:
            License.update(order.pdserial)
        else:
            order.pdserial = License.create(order.order_id)


bundles = Table('bundles', Base.metadata,
    Column('bundle', String(20), ForeignKey('products.sku'), primary_key=True),
    Column('product', String(20), ForeignKey('products.sku'), primary_key=True),
)

class Items(Base):
    __tablename__ = 'items'
    order_id = Column(Integer, ForeignKey('orders.order_id'), primary_key=True)
    sku = Column(String(20), ForeignKey('products.sku'), primary_key=True)
    price = Column(Numeric(precision=7, scale=2))
    pdserial = Column(Integer)
    product = relationship("Product")


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


anlicenses = Table('anlicenses', Base.metadata, autoload=True)
pdidx = Table('pdidx', Base.metadata, autoload=True)


class License():

    @staticmethod
    def check(regid, check_valid=False):
        """ Returns True if licence exists, if check_valid checks valid!=N
        """
        row = anlicenses.select().where(anlicenses.c.regid==regid).execute().fetchone()
        return row is not None and check_valid and row['valid'] != 'N'

    @staticmethod
    def generate():
        while True:
            regid = ''.join(random.choice("BCDFGHJKLMNPQRSTVWXZ") for _ in range(12))
            if not License.check(regid):
                return regid

    @staticmethod
    def create(order_id):
        result = pdidx.insert().values(source='Website', orderid=order_id).execute()
        DBSession.flush()
        regid = License.generate()
        pdserial = result.inserted_primary_key[0]
        anlicenses.insert().values(
                pdserial=pdserial,
                regid=regid,
                sequence=1,
                created=datetime.now(),
                lastchange=datetime.now(),
                source='Website',
                orderid=order_id,
            ).execute()
        return pdserial

    @staticmethod
    def update(pdserial):
        row = anlicenses.select().where(anlicenses.c.pdserial==pdserial).execute().fetchone()
        anlicenses.update().where(anlicenses.c.pdserial==pdserial).values(
            lastchange=datetime.now(), sequence=row['sequence']+1).execute()
