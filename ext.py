from flask_security import Security, SQLAlchemyUserDatastore

from models.user import User, Role
from corelib.db import db


class BranSQLAlchemyUserDatastore(SQLAlchemyUserDatastore):
    def get_user_name(self, identifier):
        return self._get_user(identifier, 'name')

    def get_user_email(self, identifier):
        return self._get_user(identifier, 'email')

    def _get_user(self, identifier, attr):
        user_model_query = self.user_model.query

        query = getattr(self.user_model, attr) == identifier
        rv = user_model_query.filter(query).first()
        if rv is not None:
            return rv


security = Security()
user_datastore = BranSQLAlchemyUserDatastore(db, User, Role)
