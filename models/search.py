from collections import defaultdict

from elasticsearch_dsl import (Document, Integer, Text, Boolean, Q, Keyword,
                               SF, Date, __version__)
from elasticsearch_dsl.connections import connections
from elasticsearch.helpers import parallel_bulk
from elasticsearch.exceptions import ConflictError
from flask_sqlalchemy import Pagination

from corelib.mc import cache
from corelib.db import rdb

from config import ES_HOSTS, PER_PAGE
from corelib.consts import K_POST, ONE_HOUR
from models.core import Post

connections.create_connection(hosts=ES_HOSTS)

ITEM_MC_KEY = 'core:search:{}:{}'  # item.id item.kind
POST_IDS_BY_TAG_MC_KEY = 'core:search:post_ids_by_tag:%s:%s:%s:%s'  # tag, page, order, per_page # noqa
SEARCH_FIELDS = ['title^10', 'tags^5', 'content^2']
TARGET_MAPPER = {K_POST: Post}

gauss_sf = SF('gauss',
              created_at={
                  'origin': 'now',
                  'offset': '7d',
                  'scale': '10d'
              })

score_sf = SF('script_score',
              script={
                  'lang': 'painless',
                  'inline':
                  ("doc['n_likes'].value * 2 + doc['n_collects'].value")
              })


def get_item_data(item):
    """
    返回格式化的数据字典

    `item`: Post instance
    """
    try:
        content = item.content
    except AttributeError:
        content = ''

    try:
        tags = [tag.name for tag in item.tags]
    except AttributeError:
        tags = []

    return {
        'id': item.id,
        'tags': tags,
        'content': content,
        'title': item.title,
        'kind': item.kind,
        'n_likes': item.n_likes,
        'n_comments': item.n_comments,
        'n_collects': item.n_collects,
    }


class Item(Document):
    id = Integer()
    title = Text()
    kind = Integer()
    content = Text()
    n_likes = Integer()
    n_collects = Integer()
    n_comments = Integer()
    can_show = Boolean()
    created_at = Date()
    tags = Text(fields={'raw': Keyword()})

    class Index:
        name = 'test'

    @classmethod
    def add(cls, item):
        obj = cls(**get_item_data(item))
        obj.save()
        obj.clear_mc(item.id, item.kind)
        return obj

    @classmethod
    @cache(ITEM_MC_KEY.format('{id}', '{kind}'))
    def get(cls, id, kind):
        """ 获取对象并缓存 """
        s = cls.search()
        s.query = Q('bool', must=[Q('term', id=id), Q('term', kind=kind)])
        rs = s.execute()
        if rs:
            return rs.hits[0]

    @classmethod
    def clear_mc(cls, id, kind):
        rdb.delete(ITEM_MC_KEY.format(id, kind))

    @classmethod
    def delete(cls, item):
        rs = cls.get(item.id, item.kind)
        if rs:
            super(cls, rs).delete()
            cls.clear_mc(item.id, item.kind)
            return True
        return False

    @classmethod
    def update_item(cls, item):
        obj = cls.get(item.id, item.kind)
        if obj is None:
            return cls.add(item)

        kw = get_item_data(item)

        try:
            obj.update(**kw)
        except ConflictError:
            obj.clear_mc(item.id, item.kind)
            obj = cls.get(item.id, item.kind)
            obj.update(**kw)
        obj.clear_mc(item.id, item.kind)
        return True

    @classmethod
    def get_es(cls):
        search = cls.search()
        return connections.get_connection(search._using)

    @classmethod
    def bulk_update(cls, items, chunk_size=5000, op_type='update', **kwargs):
        # TODO NOT USED
        index = cls._index._name
        type = cls._doc_type.name

        objects = ({
            '_op_type': op_type,
            '_id': f'{doc.id}_{doc.kind}',
            '_index': index,
            '_type': type,
            '_source': doc.to_dict()
        } for doc in items)
        client = cls.get_es()
        rs = list(
            parallel_bulk(client, objects, chunk_size=chunk_size, **kwargs))
        for item in items:
            cls.clear_mc(item.id, item.kind)
        return rs

    @classmethod
    def new_search(cls, query, page, order_by=None, per_page=PER_PAGE):
        """ 根据关键字搜索结果，从三个方面搜索，title权重最大, tag次之, content最后 """
        s = cls.search()
        s = s.query('multi_match', query=query, fields=SEARCH_FIELDS)  # 多行匹配

        if page < 1:
            page = 1
        start = (page - 1) * PER_PAGE
        s = s.extra(**{'from': start, 'size': per_page})
        if order_by is not None:
            s = s.sort(order_by)
        rs = s.execute()
        dct = defaultdict(list)
        for i in rs:
            dct[i.kind].append(i.id)

        items = []

        for kind, ids in dct.items():
            target_cls = TARGET_MAPPER.get(kind)
            if target_cls:
                items_ = target_cls.get_multi(ids)
                items.extend(items_)
        # Fix elasticsearch-dsl for 7.x
        total = rs.hits.total.value if __version__[0] >= 7 else rs.hits.total
        return Pagination(query, page, per_page, total, items)

    @classmethod
    @cache(POST_IDS_BY_TAG_MC_KEY %
           ('{tag}', '{page}', '{order_by}', '{per_page}'), ONE_HOUR)
    def get_post_ids_by_tag(cls, tag, page, order_by=None, per_page=PER_PAGE):
        """ 只搜索热点post，缓存期为一个小时 """
        s = cls.search()
        # s = s.query(Q('bool', must=Q('term', tags=tag)))
        s = s.query(Q('bool', must=Q('term', kind=K_POST)))
        start = (page - 1) * PER_PAGE
        if page < 1:
            page = 1
        start = (page - 1) * PER_PAGE
        s = s.extra(**{'from': start, 'size': per_page})
        if order_by is not None:
            if order_by == 'hot':
                s = s.query(Q('function_score',
                              functions=[gauss_sf, score_sf]))  # 使用高斯函数查找 noqa
            else:
                s = s.sort(order_by)
        rs = s.execute()
        ids = [obj.id for obj in rs]
        # Fix elasticsearch-dsl for 7.x
        total = rs.hits.total.value if __version__[0] >= 7 else rs.hits.total
        return Pagination(tag, page, per_page, total, ids)
