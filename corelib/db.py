# coding=utf-8

import copy
import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy, Model, DefaultMeta, _QueryProperty
from sqlalchemy.ext.declarative import (DeclarativeMeta, declarative_base,
                                        declared_attr)
from sqlalchemy import Column, DateTime, Integer, event

from sqlalchemy.ext.serializer import loads, dumps
from walrus import Database as _Database
from flask import abort

from corelib.local_cache import lc
from corelib.caching import regions, query_callable, Cache
from config import REDIS_URL


class Database(_Database):
    def get2(self, name):
        """ TODO 准备替换父类get() """
        rs = super().get(name)
        return loads(rs)

    def set2(self, name, value, ex=None, px=None, nx=False, xx=False):
        """ TODO 准备替换父类set() """
        value = dumps(value)
        return super().set(name, value, ex=ex, px=px, nx=nx, xx=xx)


class PropsItem(object):
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
        super(DatetimePropsItem, self).__init__(name, default,
                                                datetime_outputfilter)


class DatePropsItem(PropsItem):
    def __init__(self, name, default=None):
        super(DatePropsItem, self).__init__(name, default, date_outputfilter)


class PropsMixin(object):
    @property
    def _props_name(self):
        '''
        为了保证能够与corelib.mixin.wrapper能和谐的工作
        需要不同的class有不同的__props以免冲突
        '''
        return '__%s/props_cached' % self.get_uuid()

    @property
    def _props_db_key(self):
        return '%s/props' % self.get_uuid()

    def _get_props(self):
        props = lc.get(self._props_name)
        if props is None:
            props = rdb.get(self._props_db_key) or ''
            props = props and json.loads(props) or {}
            lc.set(self._props_name, props)
        return props

    def _set_props(self, props):
        rdb.set(self._props_db_key, json.dumps(props))
        lc.delete(self._props_name)

    def _destory_props(self):
        rdb.delete(self._props_db_key)
        lc.delete(self._props_name)

    _destroy_props = _destory_props

    get_props = _get_props
    set_props = _set_props

    props = property(_get_props, _set_props)

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
        session = db.session
        props = cls.get_db_props(kwargs)
        id = kwargs.pop('id', None)
        if id is not None:
            obj = cls.query.get(id)
            if obj:
                if 'update_at' not in kwargs:
                    kwargs['update_at'] = datetime.now()
                for k, v in kwargs.items():
                    setattr(obj, k, v)
                session.commit()
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
    cache_label = "default"
    cache_regions = regions
    query_class = query_callable(regions)

    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow())
    updated_at = Column(DateTime, default=None)

    def get_uuid(self):
        return '/bran/{0.__class__.__name__}/{0.id}'.format(self)

    def __repr__(self):
        return '<{0} id: {1}>'.format(self.__class__.__name__, self.id)

    @declared_attr
    def cache(cls):
        return Cache(cls, cls.cache_regions, cls.cache_label)

    @classmethod
    def get(cls, id):
        # return cls.query.get(id)  # 应该从cls.cache.get(id)取值更合适
        return cls.cache.get(id)

    @classmethod
    def get_or_404(cls, ident):
        rv = cls.get(ident)
        if rv is None:
            abort(404)
        return rv

    @classmethod
    def get_multi(cls, ids):
        return [cls.cache.get(id) for id in ids]  # 从缓存中取值

    def url(self):
        return '/{}/{}/'.format(self.__class__.__name__.lower(), self.id)

    def to_dict(self):
        columns = self.__table__.columns.keys() + ['kind']  # 增加一个`kind`的字段给`Comment`和`Post`使用  # noqa
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
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def _flush_insert_event(mapper, connection, target):
        target._flush_event(mapper, connection, target)
        if hasattr(target, 'kind'):
            from handler.tasks import reindex
            reindex.delay(target.id, target.kind, op_type='create')
        target.__flush_insert_event__(target)

    @staticmethod
    def _flush_after_update_event(mapper, connection, target):
        target._flush_event(mapper, connection, target)
        if hasattr(target, 'kind'):
            from handler.tasks import reindex
            reindex.delay(target.id, target.kind, op_type='update')
        target.__flush_after_update_event__(target)

    @staticmethod
    def _flush_before_update_event(mapper, connection, target):
        target._flush_event(mapper, connection, target)
        target.__flush_before_update_event__(target)

    @staticmethod
    def _flush_delete_event(mapper, connection, target):
        target._flush_event(mapper, connection, target)
        if hasattr(target, 'kind'):
            from handler.tasks import reindex
            reindex.delay(target.id, target.kind, op_type='delete')
        target.__flush_delete_event__(target)

    @staticmethod
    def _flush_event(mapper, connection, target):
        target.cache._flush_all(target)  # 清除target在dogpile.cache的缓存
        target.__flush_event__(target)  # 清除target在walrus的缓存

    @classmethod
    def __flush_event__(cls, target):
        pass

    @classmethod
    def __flush_delete_event__(cls, target):  # 调用clear_mc作最后的清理
        pass

    @classmethod
    def __flush_insert_event__(cls, target):  # 调用clear_mc作最后的清理
        pass

    @classmethod
    def __flush_after_update_event__(cls, target):  # 调用clear_mc作最后的清理
        pass

    @classmethod
    def __flush_before_update_event__(cls, target):  # 调用clear_mc作最后的清理
        pass

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, 'after_delete', cls._flush_delete_event)
        event.listen(cls, 'after_update', cls._flush_after_update_event)
        event.listen(cls, 'before_update', cls._flush_before_update_event)
        event.listen(cls, 'after_insert', cls._flush_insert_event)


class BindDBPropertyMixin(object):
    def __init__(cls, name, bases, d):  # 元类初始化使用
        super(BindDBPropertyMixin, cls).__init__(name, bases, d)
        db_columns = []
        for k, v in d.items():
            if isinstance(v, PropsItem):
                db_columns.append((k, v.default))
        # 针对拥有属性`PropsItem`的类增加一个特殊属性
        setattr(cls, '_db_columns', db_columns)


class CombinedMeta(BindDBPropertyMixin, DefaultMeta):
    pass


class UnLockedAlchemy(SQLAlchemy):
    """
    Custom SQLAlchemy by customing `BaseModel`, `CachingQuery`, `CombinedMeta`
    """

    def make_declarative_base(self, model, metadata=None):
        """
        Creates the declarative base that all models will inherit from.

        Called by __init__()
        """
        if not isinstance(model, DeclarativeMeta):
            model = declarative_base(cls=model,
                                     name='Model',
                                     metadata=metadata,
                                     metaclass=CombinedMeta)

        if metadata is not None and model.metadata is not metadata:
            model.metadata = metadata

        if not getattr(model, 'query_class', None):
            model.query_class = self.Query

        model.query = _QueryProperty(self)
        return model

    def apply_driver_hacks(self, app, info, options):
        """
        This method is called before engine creation and used to inject
        driver specific hacks into the options.
        """
        if 'isolation_level' not in options:
            options['isolation_level'] = 'READ COMMITTED'
        return super(UnLockedAlchemy,
                     self).apply_driver_hacks(app, info, options)


rdb = Database.from_url(REDIS_URL)  # 一个redis缓存器
db = UnLockedAlchemy(model_class=BaseModel)
