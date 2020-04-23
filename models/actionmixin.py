# coding=utf-8

import math

from config import PER_PAGE
from corelib.mc import cache
from corelib.db import rdb
from corelib.utils import incr_key
from corelib.consts import K_POST

# action_type, target_id, target_kind 统计对象<like|collect|comment>的数量
MC_KEY_GET_COUNT_BY_TARGET = 'actionmixin:ActionMixin:get_count_by_target(%s,%s,%s)'  # noqa

# action_type, user_id, target_kind 统计用户like数量
MC_KEY_GET_COUNT_BY_USER = 'actionmixin:ActionMixin:get_count_by_user(%s,%s,%s)'  # noqa

# action_type, target_id, target_kind, page 特指post的comment列表分页
MC_KEY_GET_PAGE_BY_TARGET = 'actionmixin:ActionMixin:get_page_by_target(%s,%s,%s,%s)'  # noqa

# action_type, user_id, target_id, target_kind 判断用户是否<like|collect|comment>
MC_KEY_GET_BY_TARGET = 'actionmixin:ActionMixin:get_by_target(%s,%s,%s,%s)'  # noqa

# acton_type, user_id, target_kind, page 用户<like|collect>的post列表分页
MC_KEY_GET_PAGINATE_BY_USER = 'actionmixin:ActionMixin:get_paginate_by_user(%s,%s,%s,%s)'  # noqa


class ActionMixin:
    """ ActionMixin for `CollectItem`, `CommentItem`, `LikeItem` """
    action_type = None

    @classmethod
    @cache(MC_KEY_GET_COUNT_BY_TARGET %
           ('{cls.action_type}', '{target_id}', '{target_kind}'))
    def get_count_by_target(cls, target_id, target_kind):
        return cls.query.filter_by(target_id=target_id,
                                   target_kind=target_kind).count()

    @classmethod
    @cache(MC_KEY_GET_BY_TARGET %
           ('{cls.action_type}', '{user_id}', '{target_id}', '{target_kind}'))
    def get_by_target(cls, user_id, target_id, target_kind):
        return cls.query.filter_by(user_id=user_id,
                                   target_id=target_id,
                                   target_kind=target_kind).first()

    @classmethod
    @cache(MC_KEY_GET_PAGINATE_BY_USER %
           ('{cls.action_type}', '{user_id}', '{target_kind}', '{page}'))
    def get_paginate_by_user(cls, user_id, target_kind=K_POST, page=1):
        query = cls.query.with_entities(cls.target_id).filter_by(
            user_id=user_id, target_kind=target_kind)
        posts = query.paginate(page, PER_PAGE)
        posts.items = [id for id, in posts.items]
        del posts.query  # Fix a exception during pickling
        return posts

    @classmethod
    @cache(MC_KEY_GET_COUNT_BY_USER %
           ('{cls.action_type}', '{user_id}', '{target_kind}'))
    def get_count_by_user(cls, user_id, target_kind=K_POST):
        return cls.query.filter_by(user_id=user_id,
                                   target_kind=target_kind).count()

    @classmethod
    @cache(MC_KEY_GET_PAGE_BY_TARGET %
           ('{cls.action_type}', '{target_id}', '{target_kind}', '{page}'))
    def get_page_by_target(cls, target_id, target_kind, page=1):
        query = cls.query.filter_by(target_id=target_id,
                                    target_kind=target_kind).order_by(
                                        cls.id.desc())
        if page is None:
            items = query.all()
        else:
            items = query.limit(PER_PAGE).offset(PER_PAGE * (page - 1)).all()
        return items

    @classmethod
    def __flush_insert_event__(cls, target):
        super().__flush_insert_event__(target)
        target.clear_mc(target, 1)

    @classmethod
    def __flush_delete_event__(cls, target):
        super().__flush_delete_event__(target)
        target.clear_mc(target, -1)

    # @classmethod
    # def __flush_after_update_event__(cls, target):
    #     super().__flush_after_update_event__(target)
    #     target.clear_mc(target, 1)

    # @classmethod
    # def __flush_before_update_event__(cls, target):
    #     super().__flush_before_update_event__(target)
    #     target.clear_mc(target, -1)

    @classmethod
    def clear_mc(cls, target, amount):
        action_type = cls.action_type
        assert action_type

        target_id = target.target_id
        target_kind = target.target_kind
        stat_key = MC_KEY_GET_COUNT_BY_TARGET % (action_type, target_id,
                                                 target_kind)
        total = incr_key(stat_key, amount)
        pages = math.ceil((max(total, 0) or 1) / PER_PAGE)

        user_id = target.user_id
        rdb.delete(MC_KEY_GET_BY_TARGET %
                   (action_type, user_id, target_id,
                    target_kind))
        for p in list(range(1, pages + 1)) + [None]:
            rdb.delete(
                MC_KEY_GET_PAGE_BY_TARGET %
                (action_type, target_id, target_kind, p))

        # mc by user
        stat_key = MC_KEY_GET_COUNT_BY_USER % (
            action_type, user_id, target_kind)
        total = incr_key(stat_key, amount)
        pages = math.ceil((max(total, 0) or 1) / PER_PAGE)

        for p in range(1, pages + 1):
            rdb.delete(
                MC_KEY_GET_PAGINATE_BY_USER %
                (action_type, user_id, target_kind, p))
