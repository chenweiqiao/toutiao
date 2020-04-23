# coding=utf-8

from flask_security.forms import (RegisterForm, LoginForm, Required, Length,
                                  StringField, _datastore, ValidationError,
                                  get_message, email_required, email_validator,
                                  PasswordField, password_required, EqualTo)

name_required = Required(message='没有输入名字')
name_length = Length(min=3, max=20, message='长度要在 3 - 20 之间')


def unique_user_name(form, field):
    if _datastore.get_user_name(field.data) is not None:
        msg = f'{field.data}已经被使用了'
        raise ValidationError(msg)
    if '@' in field.data:
        raise ValidationError('名字中不能使用特殊符号')


def unique_user_email(form, field):
    if _datastore.get_user_email(field.data) is not None:
        msg = get_message('EMAIL_ALREADY_ASSOCIATED', email=field.data)[0]
        raise ValidationError(msg)


class ExtendedLoginForm(LoginForm):
    email = StringField('邮箱/用户名', validators=[Required(message='未输入账号内容')])
    password = PasswordField('密码', validators=[password_required])


class ExtendedRegisterForm(RegisterForm):
    name = StringField(
        '名字', validators=[name_required, name_length, unique_user_name])
    email = StringField(
        '邮箱', validators=[email_required, email_validator, unique_user_email])
    password = PasswordField('密码', validators=[password_required])
    password_confirm = PasswordField(
        '密码确认',
        validators=[
            EqualTo('password', message='RETYPE_PASSWORD_MISMATCH'),
            password_required
        ])
