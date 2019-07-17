# coding=utf-8

import math

from config import PER_PAGE
from corelib.mc import cache, rdb
from corelib.utils import incr_key
from corelib.consts import K_POST

# action_type, target_id, target_kind
MC_KEY_STATS_N = 'like_n:%s:%s:%s'

# action_type, user_id, target_kind
MC_KEY_BY_USER_STATS_N = 'like_n_by_user:%s:%s:%s'

# action_type, target_id, target_kind, page
MC_KEY_ACTION_ITEMS = 'action_items:%s:%s:%s:%s'

# action_type, user_id, target_id, target_kind
MC_KEY_ACTION_ITEM_BY_USER = 'action_item_by_user:%s:%s:%s:%s'

# acton_type, user_id, target_kind, page
MC_KEY_ACTION_ITEMS_BY_USER = 'action_items_by_user:%s:%s:%s:%s'


class ActionMixin:
    """ ActionMixin for `CollectItem`, `CommentItem`, `LikeItem` """
    action_type = None

    @classmethod
    @cache(MC_KEY_STATS_N %
           ('{cls.action_type}', '{target_id}', '{target_kind}'))
    def get_count_by_target(cls, target_id, target_kind):
        """
        Get the amount from <`LikeItem`|`CollectItem`|`CommentItem`>
        by `target_id` and `target_kind`
        """
        return cls.query.filter_by(target_id=target_id,
                                   target_kind=target_kind).count()

    @classmethod
    @cache(MC_KEY_ACTION_ITEM_BY_USER %
           ('{cls.action_type}', '{user_id}', '{target_id}', '{target_kind}'))
    def get_by_target(cls, user_id, target_id, target_kind):
        """
        Get a item which <collected|liked> by user
        from <`LikeItem`|`CollectItem`>,
        each item only once or none.
        """
        return cls.query.filter_by(user_id=user_id,
                                   target_id=target_id,
                                   target_kind=target_kind).first()

    @classmethod
    @cache(MC_KEY_ACTION_ITEMS_BY_USER % ('{cls.action_type}', '{user_id}',
           '{target_kind}', '{page}'))
    def get_target_ids_by_user(cls, user_id, target_kind=K_POST, page=1):
        """
        Get a list of <`CollectItem`|`LikeItem`> which <collected|liked>
        by user
        """
        query = cls.query.with_entities(cls.target_id).filter_by(
            user_id=user_id, target_kind=target_kind)
        posts = query.paginate(page, PER_PAGE)
        posts.items = [id for id, in posts.items]
        del posts.query  # Fix a exception during pickling
        return posts

    @classmethod
    @cache(MC_KEY_BY_USER_STATS_N %
           ('{cls.action_type}', '{user_id}', '{target_kind}'))
    def get_count_by_user(cls, user_id, target_kind=K_POST):
        """
        Get the amount of <`CollectItem`|`LikeItem`|`Comment`> by user
        """
        # TODO NOT USED
        return cls.query.filter_by(user_id=user_id,
                                   target_kind=target_kind).count()

    @classmethod
    @cache(MC_KEY_ACTION_ITEMS %
           ('{cls.action_type}', '{target_id}', '{target_kind}', '{page}'))
    def gets_by_target(cls, target_id, target_kind, page=1):
        """ Get a list of `CommentItem` """
        query = cls.query.filter_by(target_id=target_id,
                                    target_kind=target_kind).order_by(
                                        cls.id.desc())
        if page is None:
            items = query.all()
        else:
            items = query.limit(PER_PAGE).offset(PER_PAGE * (page - 1)).all()
        return items

    @classmethod
    def is_action_by(cls, user_id, target_id, target_kind):
        return bool(cls.get_by_target(user_id, target_id, target_kind))

    @classmethod
    def __flush_insert_event__(cls, target):
        super().__flush_insert_event__(target)
        target.clear_mc(target, 1)

    @classmethod
    def __flush_delete_event__(cls, target):
        super().__flush_delete_event__(target)
        target.clear_mc(target, -1)

    @classmethod
    def __flush_after_update_event__(cls, target):
        super().__flush_after_update_event__(target)
        target.clear_mc(target, 1)

    @classmethod
    def __flush_before_update_event__(cls, target):
        super().__flush_before_update_event__(target)
        target.clear_mc(target, -1)

    @classmethod
    def clear_mc(cls, target, amount):
        action_type = cls.action_type
        assert action_type

        target_id = target.target_id
        target_kind = target.target_kind
        stat_key = MC_KEY_STATS_N % (action_type, target_id, target_kind)
        total = incr_key(stat_key, amount)  # 对该条目的被<点赞|评论|收藏>总数进行加减
        pages = math.ceil((max(total, 0) or 1) / PER_PAGE)

        user_id = target.user_id
        rdb.delete(MC_KEY_ACTION_ITEM_BY_USER %
                   (action_type, user_id, target_id,
                    target_kind))  # 清除被用户<like|collect>的条目 # noqa
        for p in list(range(1, pages + 1)) + [None]:
            rdb.delete(
                MC_KEY_ACTION_ITEMS %
                (action_type, target_id, target_kind, p))  # 清除该条目下的所有评论页码

        # mc by user
        stat_key = MC_KEY_BY_USER_STATS_N % (action_type, user_id, target_kind
                                             )  # 暂时没用到 # noqa
        total = incr_key(stat_key, amount)
        pages = math.ceil((max(total, 0) or 1) / PER_PAGE)

        for p in range(1, pages + 1):
            rdb.delete(MC_KEY_ACTION_ITEMS_BY_USER %
                       (action_type, user_id, target_kind,
                        p))  # 清除用户<like|collect>的所有页码缓存
