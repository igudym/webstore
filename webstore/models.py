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


anlicenses = Table('anlicenses', Base.metadata, autoload=True)
pdidx = Table('pdidx', Base.metadata, autoload=True)
anproducts = Table('anproducts', Base.metadata, autoload=True)


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
    paypal_token = Column(String(30))

    def _add_product(self, item, prodserial):
        anproducts.insert().values(
            product=item.sku,
            pdserial=self.pdserial,
            prodserial=prodserial,
            source="Website",
            orderid=self.order_id,
            orderdate=self.created,
            valid='Y'
        ).execute()

    def confirm(self):
        self.status = 'paid'
        if self.pdserial:
            License.update(self.pdserial)
        else:
            self.pdserial = License.create(self.order_id)
        for item in self.items:
            prodserial = 0
            if item.product.serialtab:
                tab = Table(item.product.serialtab, Base.metadata, autoload=True)
                res = tab.insert().values(
                    pdserial=self.pdserial,
                    source="Website",
                    orderid=self.order_id
                ).execute()
                prodserial = res.inserted_primary_key[0]
            if item.product.bundle:
                for subitem in item.product.items:
                    self._add_product(subitem, prodserial)
            else:
                self._add_product(item, prodserial)

    @staticmethod
    def confirm_order(order_id):
        order = DBSession.query(Order).filter(Order.order_id==order_id).one()
        order.confirm()
        return order


bundles = Table('bundles', Base.metadata,
    Column('bundle', String(20), ForeignKey('products.sku'), primary_key=True),
    Column('product', String(20), ForeignKey('products.sku'), primary_key=True),
)

class Items(Base):
    __tablename__ = 'items'
    order_id = Column(Integer, ForeignKey('orders.order_id'), primary_key=True)
    sku = Column(String(20), ForeignKey('products.sku'), primary_key=True)
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
    serialtab = Column(String(50))


class License():

    @staticmethod
    def check(regid, check_valid=False):
        """ Returns 'pdserial' if licence exists, if check_valid checks valid!=N
        """
        row = anlicenses.select().where(anlicenses.c.regid==regid).execute().fetchone()
        return row['pdserial'] if row is not None and (
                                    not check_valid or row['valid'] != 'N') else False

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

    @staticmethod
    def products(pdserial):
        statement = anproducts.select().where(anproducts.c.pdserial==pdserial)
        for row in statement.execute().fetchall():
            yield row