from werkzeug.utils import cached_property
from flask import Flask as _Flask, Request as _Request
from flask_security import current_user

from models.user import User


class Request(_Request):
    @cached_property
    def user_id(self):
        user = current_user
        return user and (user.is_authenticated and user.id) or None

    @cached_property
    def user(self):
        return User.get(self.user_id) if self.user_id else None


class Flask(_Flask):
    """ Alternate `Request`， add `user_id` and `user` property """
    request_class = Request
