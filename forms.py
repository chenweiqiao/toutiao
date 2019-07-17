# coding=utf-8

from flask_security import current_user
from flask_security.forms import (
    RegisterForm, LoginForm, Required, Length, StringField, _datastore,
    ValidationError, SendConfirmationForm, get_message, email_required,
    email_validator, valid_user_email, PasswordField, password_required,
    verify_and_update_password, EqualTo)

name_required = Required(message='没有输入名字')
name_length = Length(min=3, max=20, message='长度要在 3 - 20 之间')


def valid_user_email_fro_oauth(form, field):
    if not field.data:
        return
    form.user = _datastore.get_user(field.data)
    if form.user is None:
        raise ValidationError(get_message('USER_DOES_NOT_EXIST')[0])


def phone_validate(form, field):
    phone = str(field.data)
    if not phone:
        return
    if not (len(phone) == 11 and phone[0] == '1'
            and phone[1] in ('3', '5', '8')):
        raise ValidationError('手机号码格式错误')


def unique_user_name(form, field):
    if _datastore.get_user_name(field.data) is not None:
        msg = f'{field.data}已经被使用了'
        raise ValidationError(msg)
    if '@' in field.data:
        raise ValidationError('名字中不能使用特殊符号')


def unique_email(form, field):
    if form.origin_email.data == field.data:
        raise ValidationError(('请使用和当前邮箱不同的地址'))


def unique_phone(form, field):
    if form.origin_phone_number.data == field.data:
        raise ValidationError(('请更改成不同的手机号码'))


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


# TODO
class ResetEmailForm(SendConfirmationForm):
    origin_email = StringField(
        '当前邮箱(只读)',
        render_kw={'readonly': True},
        validators=[email_required, email_validator, valid_user_email])
    email = StringField('新邮箱',
                        validators=[
                            email_required, email_validator, unique_user_email,
                            unique_email
                        ])
    password = PasswordField('账户密码', validators=[password_required])

    def validate(self):
        if not super(SendConfirmationForm, self).validate():
            return False
        if not verify_and_update_password(self.password.data, current_user):
            self.password.errors.append('密码输入错误')
            return False
        return True


# TODO
class ResetEmailForOauthForm(SendConfirmationForm):
    origin_email = StringField('当前邮箱(只读)',
                               render_kw={'readonly': True},
                               validators=[valid_user_email_fro_oauth])
    email = StringField('新邮箱',
                        validators=[
                            email_required, email_validator, unique_user_email,
                            unique_email
                        ])
    password = PasswordField('账户密码(可选)')
