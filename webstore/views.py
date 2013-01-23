from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .models import (
    DBSession,
    License,
    Product,
    )


@view_config(route_name='home', renderer='templates/order.pt')
def order_view(request):
    print '------------------------------------------------------------'
    if request.POST:
        lic = License()
        regid = lic.create()
        print regid
    try:
        #one = DBSession.query(MyModel).filter(MyModel.name == 'one').first()
        bundles = DBSession.query(Product).filter(Product.bundle).all()
        modules = DBSession.query(Product).filter(~Product.bundle).all()
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

