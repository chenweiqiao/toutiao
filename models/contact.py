"""
|————————————————————————————————————————————————————————|
| contact | `followers` --> current_user --> `following` |
|————————————————————————————————————————————————————————|
|  count  |    0...n             1              0...n    |
|————————————————————————————————————————————————————————|
"""

import math

from corelib.db import db
from config import PER_PAGE
from corelib.mc import cache
from corelib.db import rdb
from models.exceptions import NotAllowedException

# from_id, page 正在关注的列表分页
MC_KEY_GET_FOLLOWING_PAGINATE = 'contact:Contact:get_following_paginate(%s,%s)'

# to_id, page 关注者列表分页
MC_KEY_GET_FOLLOWERS_PAGINATE = 'contact:Contact:get_followers_paginate(%s,%s)'

# from_id, to_id  # 两用户是否关注
MC_KEY_GET_FOLLOW_ITEM = 'contact:Contact:get_follow_item(%s,%s)'


class Contact(db.Model):
    """ 关注关系 """
    __tablename__ = 'contacts'
    from_id = db.Column(db.Integer)  # 关注者 follower
    to_id = db.Column(db.Integer)  # 被关注者 followed

    __table_args__ = (
        db.UniqueConstraint('from_id', 'to_id', name='uk_from_to'),
        db.Index('idx_to_time_from', to_id, 'created_at', from_id),
        db.Index('idx_time_to_from', 'created_at', to_id, from_id),
    )

    def update(self, **kwargs):
        raise NotAllowedException

    @classmethod
    def create(cls, **kwargs):
        ok, obj = super().create(**kwargs)
        cls.clear_mc(obj, 1)
        if ok:
            from handler.tasks import feed_followed_posts_to_follower
            feed_followed_posts_to_follower.delay(obj.from_id, obj.to_id)
        return ok, obj

    def delete(self):
        super().delete()
        self.clear_mc(self, -1)
        from handler.tasks import remove_user_posts_from_feed
        remove_user_posts_from_feed.delay(self.from_id, self.to_id)

    @classmethod
    @cache(MC_KEY_GET_FOLLOWERS_PAGINATE % ('{to_id}', '{page}'))
    def get_followers_paginate(cls, to_id, page=1):
        """ 获取`followers`列表分页 """
        query = cls.query.with_entities(cls.from_id).filter_by(
            to_id=to_id)
        followers = query.paginate(page, PER_PAGE)
        followers.items = [id for id, in followers.items]
        del followers.query
        return followers

    @classmethod
    @cache(MC_KEY_GET_FOLLOWING_PAGINATE % ('{from_id}', '{page}'))
    def get_following_paginate(cls, from_id, page=1):
        """ 获取`following`正在关注列表分页 """
        query = cls.query.with_entities(cls.to_id).filter_by(
            from_id=from_id)
        following = query.paginate(page, PER_PAGE)
        following.items = [id for id, in following.items]
        del following.query
        return following

    @classmethod
    @cache(MC_KEY_GET_FOLLOW_ITEM % ('{from_id}', '{to_id}'))
    def get_follow_item(cls, from_id, to_id):
        """ 获取两用户是否关注 """
        return cls.query.filter_by(from_id=from_id, to_id=to_id).first()

    @classmethod
    def clear_mc(cls, target, amount):
        """ 关注和取消都要清理缓存及更新相关对象 """
        to_id = target.to_id
        from_id = target.from_id

        st = userFollowStats.get_or_create(to_id)
        follower_count = st.follower_count or 0
        st.follower_count = follower_count + amount
        st.save()  # 注意，放在sqlalchemy的清理钩子里，会报错

        st = userFollowStats.get_or_create(from_id)
        following_count = st.following_count or 0
        st.following_count = following_count + amount
        st.save()

        rdb.delete(MC_KEY_GET_FOLLOW_ITEM % (from_id, to_id))

        for user_id, total, mc_key in (
                (to_id, follower_count, MC_KEY_GET_FOLLOWERS_PAGINATE),
                (from_id, following_count, MC_KEY_GET_FOLLOWING_PAGINATE)):
            pages = math.ceil((max(total, 0) or 1) / PER_PAGE)
            for p in range(1, pages + 1):
                rdb.delete(mc_key % (user_id, p))


class userFollowStats(db.Model):
    """ 关注关系统计数量， `id`作为`user_id` """
    follower_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)

    @classmethod
    def get_or_create(cls, id, **kw):
        st = cls.get(id)
        if not st:
            st = cls(id=id)
            st.save()
        return st
