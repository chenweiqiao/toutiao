# coding=utf-8

import copy
import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy, Model, DefaultMeta, declarative_base
from sqlalchemy import Column, DateTime, Integer, event
from sqlalchemy.exc import InvalidRequestError
from flask import abort
from walrus import Database

from corelib.local_cache import lc
from config import REDIS_URL
from corelib.mc import cache

MC_KEY_GET_ID = 'db:BaseModel:get(%s,%s)'  # obj_type:obj_id 缓存`Model.get(id)`


class PropsItem:
    def __init__(self, name, default=None, output_filter=None, pre_set=None):
        self.name = name
        self.default = default
        self.output_filter = output_filter
        self.pre_set = pre_set

    def __get__(self, obj, objtype):
        r = obj.get_props_item(self.name, None)
        if r is None:
            return copy.deepcopy(self.default)
        elif self.output_filter:
            return self.output_filter(r)
        else:
            return r

    def __set__(self, obj, value):
        if self.pre_set:
            value = self.pre_set(value)
        obj.set_props_item(self.name, value)

    def __delete__(self, obj):
        obj.delete_props_item(self.name)


def datetime_outputfilter(v):
    return datetime.strptime(v, '%Y-%m-%d %H:%M:%S') if v else None


def date_outputfilter(v):
    return datetime.strptime(v, '%Y-%m-%d').date() if v else None


class DatetimePropsItem(PropsItem):
    def __init__(self, name, default=None):
        super().__init__(name, default, datetime_outputfilter)


class DatePropsItem(PropsItem):
    def __init__(self, name, default=None):
        super().__init__(name, default, date_outputfilter)


class PropsMixin:
    """ 专门处理`posts`和`comments` """
    @property
    def _props_lc_key(self):
        return '__%s/props_cached' % self.get_uuid()

    @property
    def _props_db_key(self):
        return '%s/props' % self.get_uuid()

    def _get_props(self):
        props = lc.get(self._props_lc_key)
        if props is None:
            props = rdb.get(self._props_db_key) or ''
            props = props and json.loads(props) or {}
            lc.set(self._props_lc_key, props)
        return props

    def _set_props(self, props):
        """ param `props` is a mapping object """
        rdb.set(self._props_db_key, json.dumps(props))
        lc.delete(self._props_lc_key)

    def _destory_props(self):
        rdb.delete(self._props_db_key)
        lc.delete(self._props_lc_key)

    props = property(_get_props, _set_props, _destory_props)

    def set_props_item(self, key, value):
        props = self.props
        props[key] = value
        self.props = props

    def delete_props_item(self, key):
        props = self.props
        props.pop(key, None)
        self.props = props

    def get_props_item(self, key, default=None):
        return self.props.get(key, default)

    def incr_props_item(self, key):
        n = self.get_props_item(key, 0)
        n += 1
        self.set_props_item(key, n)
        return n

    def decr_props_item(self, key, min=0):
        n = self.get_props_item(key, 0)
        n -= 1
        n = n > 0 and n or 0
        self.set_props_item(key, n > min and n or min)
        return n

    def update_props(self, data):
        props = self.props
        props.update(data)
        self.props = props

    @classmethod
    def get_db_props(cls, kwargs):
        props = {}
        for col, default in cls._db_columns:
            props[col] = kwargs.pop(col, default)
        return props

    @classmethod
    def create_or_update(cls, **kwargs):
        props = cls.get_db_props(kwargs)
        id = kwargs.pop('id', None)
        if id is not None:  # for update obj
            obj = cls.query.get(id)
            if obj:
                if 'update_at' not in kwargs:
                    kwargs['update_at'] = datetime.now()
                for k, v in kwargs.items():
                    setattr(obj, k, v)
                obj.save()
                cls.update_db_props(obj, props)
                return False, obj
        obj = cls(**kwargs)
        obj.save()
        cls.update_db_props(obj, props)
        return True, obj

    @classmethod
    def update_db_props(cls, obj, db_props):
        for prop, value in db_props.items():
            obj.set_props_item(prop, value)


class BaseModel(PropsMixin, Model):
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow())
    updated_at = Column(DateTime, default=None)

    __table_args__ = {'mysql_charset': 'utf8mb4'}

    def get_uuid(self):
        return '/bran/{0.__class__.__name__}/{0.id}'.format(self)

    def __repr__(self):
        return '<{0} id: {1}>'.format(self.__class__.__name__, self.id)

    @classmethod
    @cache(MC_KEY_GET_ID % ('{cls.__name__}', '{id}'))
    def get(cls, id):
        return cls.query.get(id)

    @classmethod
    def get_or_404(cls, ident):
        rv = cls.get(ident)
        if rv is None:
            abort(404)
        return rv

    @classmethod
    def get_multi(cls, ids):
        return [cls.get(id) for id in ids]

    def url(self):
        return '/{}/{}/'.format(self.__class__.__name__.lower(), self.id)

    def to_dict(self):
        columns = self.__table__.columns.keys() + ['kind']  # `kind`是给`Comment`表和`Post`表使用  # noqa
        dct = {key: getattr(self, key, None) for key in columns}
        return dct

    @classmethod
    def create(cls, **kwargs):
        props = cls.get_db_props(kwargs)
        if not kwargs:
            return False, None
        filter = cls.query.filter_by(**kwargs)
        obj = filter.first()
        if obj:
            return False, obj
        obj = cls(**kwargs)
        obj.save()
        cls.update_db_props(obj, props)
        return True, obj

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.save()

    def save(self):
        try:
            db.session.add(self)
        except InvalidRequestError: # 这个错误是由于User.get(id)返回的是缓存对象，而Request那里调用了current_user，从数据库读取user，因此在db.session留下了对象；缓存对象更新某些字段后,db.session里的对象并不能感知缓存对象的变化，需要用merge方法合并到session中 # noqa
            db.session.merge(self)  # Fix `sqlalchemy.exc.InvalidRequestError: Can't attach instance xxx; another instance with key zzz is already present in this session.` # noqa
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def _flush_insert_event(mapper, connection, target):
        if hasattr(target, 'kind'):
            from handler.tasks import reindex
            reindex.apply_async(args=(target.id, target.kind, 'create'), countdown=1)  # 此时新增post及它的tags还没写入数据库，而reindex会提前读取post.tags导致缓存里数据为空 # noqa
        target.__flush_insert_event__(target)

    @staticmethod
    def _flush_delete_event(mapper, connection, target):
        if hasattr(target, 'kind'):
            from handler.tasks import reindex
            reindex.delay(target.id, target.kind, op_type='delete')
        target.__flush_delete_event__(target)

    @staticmethod
    def _flush_after_update_event(mapper, connection, target):
        if hasattr(target, 'kind'):
            from handler.tasks import reindex
            reindex.delay(target.id, target.kind, op_type='update')
        target.__flush_after_update_event__(target)

    @staticmethod
    def _flush_before_update_event(mapper, connection, target):
        target.__flush_before_update_event__(target)

    @classmethod
    def __flush_event__(cls, target):
        rdb.delete(MC_KEY_GET_ID % (target.__class__.__name__, target.id))

    @classmethod
    def __flush_insert_event__(cls, target):
        pass

    @classmethod
    def __flush_delete_event__(cls, target):
        target.__flush_event__(target)

    @classmethod
    def __flush_after_update_event__(cls, target):
        target.__flush_event__(target)

    @classmethod
    def __flush_before_update_event__(cls, target):
        pass

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, 'after_insert', cls._flush_insert_event)
        event.listen(cls, 'after_delete', cls._flush_delete_event)
        event.listen(cls, 'after_update', cls._flush_after_update_event)
        event.listen(cls, 'before_update', cls._flush_before_update_event)


class BindDBPropertyMeta(DefaultMeta):
    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)
        db_columns = []
        for k, v in d.items():
            if isinstance(v, PropsItem):
                db_columns.append((k, v.default))
        cls._db_columns = db_columns


rdb = Database.from_url(REDIS_URL)
db = SQLAlchemy(model_class=declarative_base(cls=BaseModel,
                                             metaclass=BindDBPropertyMeta,
                                             name='Model'))
