from datetime import datetime
import braintree
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError
from dbsession import DBSession
from paypal import PayPalInterface, PayPalAPIResponseError

from .models import (
    License,
    Product,
    Order,
    Items,
    anlicenses)


def _get_paypal(settings):
    return PayPalInterface(
        API_ENVIRONMENT=settings['paypal.API_ENVIRONMENT'],
        API_USERNAME=settings['paypal.API_USERNAME'],
        API_PASSWORD=settings['paypal.API_PASSWORD'],
        API_SIGNATURE=settings['paypal.API_SIGNATURE'],
    )


@view_config(name='admin', renderer='templates/dashboard.pt')
def dashboard_view(request):
    orders = DBSession.query(Order).all()
    licenses = DBSession.query(anlicenses).all()
    return {'orders': orders, 'licenses': licenses}


@view_config(name='cancel', renderer='templates/error.pt')
def cancel_view(request):
    token = request.params['token']
    order = DBSession.query(Order).filter(Order.paypal_token==token).one()
    order.status = 'canceled'
    message = 'Order canceled'
    return {'message': message, 'url': request.application_url}


@view_config(name='payment', renderer='templates/success.pt')
def payment_view(request):
    if 'token' in request.params: # paypal return
        token = request.params['token']
        order = DBSession.query(Order).filter(Order.paypal_token==token).one()
        paypal = _get_paypal(request.registry.settings)
        try:
            result = paypal.get_express_checkout_details(token=token)
            print result
            payerid = result['PAYERID']
            result = paypal.do_express_checkout_payment(token=token, payerid=payerid,
                PAYMENTACTION='SALE',
                PAYMENTREQUEST_0_PAYMENTACTION='SALE',
                PAYMENTREQUEST_0_AMT=str(order.total)
                )
            print result
        except PayPalAPIResponseError, e:
            return render_to_response('templates/error.pt',
                {'message': str(e), 'url': request.application_url})
        order.confirm()
    else: # braintree
        result = braintree.TransparentRedirect.confirm(request.query_string)
        if result.is_success:
            order = Order.confirm_order(result.transaction.order_id)
        else:
            message = "Errors: %s" % " ".join(error.message for error in
                result.errors.deep_errors)
            return render_to_response('templates/error.pt',
                {'message': message, 'url': request.application_url})
    row = anlicenses.select().where(anlicenses.c.pdserial==order.pdserial).execute().fetchone()
    return {'order': order,
            'regid': row['regid'],
            'new': row['sequence'] == 1
            }


@view_config(route_name='home', renderer='templates/order.pt')
def order_view(request):
    if request.POST:
        v = request.POST
        if 'proceed' in request.POST: # Paypal processing
            paypal = _get_paypal(request.registry.settings)
            order = DBSession.query(Order).filter(Order.order_id==v['order']).one()
            description = ', '.join(i.product.name for i in order.items)
            result = paypal.set_express_checkout(
                PAYMENTREQUEST_0_AMT=str(order.total),
                PAYMENTREQUEST_0_ITEMAMT=str(order.total),
                PAYMENTREQUEST_0_DESC=description + '. Total: $' + str(order.total),
                PAYMENTREQUEST_0_PAYMENTACTION='SALE',
                RETURNURL=request.application_url + '/payment',
                CANCELURL=request.application_url + '/cancel',
            )
            if result.success:
                token = result['TOKEN']
                order.paypal_token = token
                return HTTPFound(location=paypal.generate_express_checkout_redirect_url(token))

        order = Order()
        order.first_name = v['first_name']
        order.last_name = v['last_name']
        order.email = v['email']
        if v['lic'] == 'upgrade':
            row = anlicenses.select().where(anlicenses.c.regid==v['license']).execute().fetchone()
            order.pdserial = row['pdserial']
        order.total = 0
        order.payment = v['method']
        order.status = 'pending'
        order.created = datetime.now()
        if v['method'] == 'card':
            order.addr1 = v['address1']
            order.addr2 = v['address2']
            order.city = v['city']
            order.state = v['state']
            order.zipcode = v['zip']
            order.country = v['country']
        DBSession.add(order)
        DBSession.flush()

        if v['bundle'] != '0':
            bundle = Items()
            bundle.order_id = order.order_id
            bundle.sku = v['bundle']
            DBSession.add(bundle)
            DBSession.flush()
            order.total = bundle.product.price
        for sku in v.getall('module'):
            module = Items()
            module.order_id = order.order_id
            module.sku = sku
            DBSession.add(module)
            DBSession.flush()
            order.total = order.total + module.product.price
        if v['method'] == 'card':
            settings = request.registry.settings
            if settings['braintree.environment'] == 'Production':
                env = braintree.Environment.Production
            else:
                env = braintree.Environment.Sandbox
            braintree.Configuration.configure(env,
                merchant_id=settings['braintree.merchant_id'],
                public_key=settings['braintree.public_key'],
                private_key=settings['braintree.private_key'])
            tr_data = braintree.Transaction.tr_data_for_sale(
                {"transaction": {"type": "sale",
                                 "order_id": str(order.order_id),
                                 "amount": str(order.total),
                                 "options": {"submit_for_settlement": True}}},
                request.application_url + '/payment')
            braintree_url = braintree.TransparentRedirect.url()


            return render_to_response('templates/payment.pt',
                {'order': order, 'v': v, 'tr_data':tr_data, 'braintree_url': braintree_url},
                request=request)
        elif v['method'] == 'paypal':
            return render_to_response('templates/payment.pt',
                {'order': order, 'v': v},
                request=request)
    try:
        bundles = DBSession.query(Product).filter(Product.bundle).order_by(Product.display_order).all()
        modules = DBSession.query(Product).filter(~Product.bundle).order_by(Product.display_order).all()
    except DBAPIError:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    return {'bundles': bundles, 'modules': modules}

@view_config(renderer="json", name="check_license.json")
def check_licence(request):
    if 'license' in request.params:
        lic = License()
        return ['valid' if lic.check(request.params['license'], True) else 'invalid']
    return ['invalid request']

conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_webstore_db" script
    to initialize your database tables.  Check your virtual 
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""

