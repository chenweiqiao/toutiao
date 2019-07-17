# coding=utf-8

from flask_security import login_user, current_user
from flask_security.utils import verify_password as _verify_password
from flask_httpauth import HTTPBasicAuth

from . import user_datastore, json_api, ApiException, errors

auth = HTTPBasicAuth()  # 配合json_api蓝图使用


@auth.verify_password
def verify_password(email_or_name, password):
    if current_user.is_authenticated and current_user.id:
        return True

    if email_or_name == '' or password == '':
        return False

    user = user_datastore.get_user_email(email_or_name) or\
        user_datastore.get_user_name(email_or_name)
    if not user:
        return False

    return login_user(user) if _verify_password(password, user.password) \
        else False


@auth.error_handler
def auth_error():
    raise ApiException(errors.access_forbidden)


@json_api.before_request
@auth.login_required  # 由httpauth验证保护json_api的全部路由
def auth_before_request():
    pass
