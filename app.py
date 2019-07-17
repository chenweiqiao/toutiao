from flask import render_template
from flask_security import current_user
from werkzeug.wsgi import DispatcherMiddleware
from social_flask.routes import social_auth
from social_flask_sqlalchemy.models import init_social

import config
from ext import security, db
from corelib.flask import Flask
from corelib.utils import update_url_query
from corelib.exmail import send_mail_task as _send_mail_task
from forms import ExtendedLoginForm, ExtendedRegisterForm
import views.index as index
import views.account as account
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
    app.add_template_global(current_user, 'current_user')
    app.add_template_global(update_url_query)


def create_app():
    from ext import user_datastore
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    init_social(app, db.session)

    _state = security.init_app(app,
                               user_datastore,
                               confirm_register_form=ExtendedRegisterForm,
                               login_form=ExtendedLoginForm)
    security._state = _state
    security.send_mail_task(_send_mail_task)
    app.security = security

    app.context_processor(_inject_processor)
    _inject_template_global(app)

    app.register_blueprint(index.bp, url_prefix='/')
    app.register_blueprint(account.bp, url_prefix='/')
    app.register_blueprint(social_auth)

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/api': api})

    return app


app = create_app()


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
    db.session.remove()
