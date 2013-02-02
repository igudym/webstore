from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from pyramid_mailer import mailer_factory_from_settings

from .dbsession import (
    DBSession,
    Base,
    )


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.reflect(only=('anlicenses', 'pdidx', 'anproducts'))
    config = Configurator(settings=settings)
    config.registry['mailer'] = mailer_factory_from_settings(settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.scan()
    return config.make_wsgi_app()
