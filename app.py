from flask import render_template
from flask_security import current_user
from flask_sqlalchemy import get_debug_queries
try:
    from werkzeug.wsgi import DispatcherMiddleware
except ImportError:
    from werkzeug.middleware.dispatcher import DispatcherMiddleware

import config
from corelib.db import db
from ext import security, user_datastore
from corelib.flask import Flask
from corelib.utils import update_url_query
from corelib.exmail import send_mail_task as _send_mail_task
from forms import ExtendedLoginForm, ExtendedRegisterForm
from views import index, account
from views.api import json_api as api


def _inject_processor():
    return dict(isinstance=isinstance,
                current_user=current_user,
                getattr=getattr,
                len=len,
                user=current_user)


def _inject_template_global(app):
    app.add_template_global(dir)
    app.add_template_global(len)
    app.add_template_global(hasattr)
    app.add_template_global(current_user)
    app.add_template_global(update_url_query)


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    security.init_app(app,
                      user_datastore,
                      confirm_register_form=ExtendedRegisterForm,
                      login_form=ExtendedLoginForm)
    security.send_mail_task(_send_mail_task)

    app.context_processor(_inject_processor)
    _inject_template_global(app)

    app.register_blueprint(index.bp, url_prefix='/')
    app.register_blueprint(account.bp, url_prefix='/')

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/api': api})

    return app


app = create_app()


@app.errorhandler(404)
def page_not_found(exception):
    return render_template('404.html'), 404


@app.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
    db.session.remove()


@app.after_request
def after_request(response):
    if not config.SQLALCHEMY_RECORD_QUERIES:
        return response
    for query in get_debug_queries():
        if query.duration > 0:
            app.logger.warning(
                ('\nContext:{}\nSLOW QUERY: {}\nParameters: {}\n'
                 'Duration: {}\n').format(query.context, query.statement,
                                          query.parameters, query.duration))
    return response
