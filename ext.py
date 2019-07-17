# coding=utf-8

from flask_security import Security, SQLAlchemyUserDatastore

from models.user import User, Role, db


class BranSQLAlchemyUserDatastore(SQLAlchemyUserDatastore):
    def get_user_name(self, identifier):
        return self._get_user(identifier, 'name')

    def get_user_email(self, identifier):
        return self._get_user(identifier, 'email')

    def _get_user(self, identifier, attr):
        """ 模拟`super().get_user()`，把查询`name`和`email`分开 """
        user_model_query = self.user_model.query
        if hasattr(self.user_model, 'roles'):
            from sqlalchemy.orm import joinedload
            user_model_query = user_model_query.options(
                joinedload('roles'))  # join 连接 # noqa

        # type(query) is `sqlalchemy.sql.elements.BinaryExpression`
        query = getattr(self.user_model, attr) == identifier
        rv = user_model_query.filter(query).first()
        if rv is not None:
            return rv


security = Security()
user_datastore = BranSQLAlchemyUserDatastore(db, User, Role)
