import math

from corelib.db import db
from config import PER_PAGE
from corelib.mc import cache, rdb
from models.exceptions import NotAllowedException

MC_KEY_FOLLOWING = 'following:%s:%s'  # user_id, page
MC_KEY_FOLLOWERS = 'followers:%s:%s'  # user_id, page
MC_KEY_FOLLOW_ITEM = 'is_followed:%s:%s'  # from_id, to_id


class Contact(db.Model):
    """ 关注关系 """
    __tablename__ = 'contacts'
    from_id = db.Column(db.Integer)  # 关注人
    to_id = db.Column(db.Integer)  # 被关注人

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
            from handler.tasks import feed_to_followers
            feed_to_followers.delay(obj.from_id, obj.to_id)
        return ok, obj

    def delete(self):
        super().delete()
        self.clear_mc(self, -1)
        from handler.tasks import remove_user_posts_from_feed
        remove_user_posts_from_feed.delay(self.from_id, self.to_id)

    @classmethod
    @cache(MC_KEY_FOLLOWERS % ('{user_id}', '{page}'))
    def get_follower_ids(cls, user_id, page=1):
        """ 获取该用户的粉丝 """
        query = cls.query.with_entities(cls.from_id).filter_by(
            to_id=user_id)
        followers = query.paginate(page, PER_PAGE)
        followers.items = [id for id, in followers.items]
        del followers.query
        return followers

    @classmethod
    @cache(MC_KEY_FOLLOWING % ('{user_id}', '{page}'))
    def get_following_ids(cls, user_id, page=1):
        """ 获取该用户关注的人 """
        query = cls.query.with_entities(cls.to_id).filter_by(
            from_id=user_id)
        following = query.paginate(page, PER_PAGE)
        following.items = [id for id, in following.items]
        del following.query
        return following

    @classmethod
    @cache(MC_KEY_FOLLOW_ITEM % ('{from_id}', '{to_id}'))
    def get_follow_item(cls, from_id, to_id):
        """ 获取两用户是否有关注 """
        return cls.query.filter_by(from_id=from_id, to_id=to_id).first()

    @classmethod
    def clear_mc(cls, target, amount):
        """ 每次创建和删除都要清理缓存，没有通过db.Model里的sql的事件触发清理工作 """
        to_id = target.to_id
        from_id = target.from_id

        st = userFollowStats.get_or_create(to_id)
        follower_count = st.follower_count or 0
        st.follower_count = follower_count + amount
        st.save()
        st = userFollowStats.get_or_create(from_id)
        following_count = st.following_count or 0
        st.following_count = following_count + amount
        st.save()

        rdb.delete(MC_KEY_FOLLOW_ITEM % (from_id, to_id))

        for user_id, total, mc_key in (
                (to_id, follower_count, MC_KEY_FOLLOWERS),
                (from_id, following_count, MC_KEY_FOLLOWING)):
            pages = math.ceil((max(total, 0) or 1) / PER_PAGE)
            for p in range(1, pages + 1):
                rdb.delete(mc_key % (user_id, p))


class userFollowStats(db.Model):
    """ 关注关系统计数量 """
    follower_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)

    __table_args__ = {
        'mysql_charset': 'utf8'
    }

    @classmethod
    def get(cls, id):
        return cls.cache.get(id)

    @classmethod
    def get_or_create(cls, id, **kw):
        st = cls.get(id)
        if not st:
            st = cls(id=id)
            st.save()
        return st
