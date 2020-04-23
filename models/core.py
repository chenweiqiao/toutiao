import math
from urllib.request import urlparse

from config import PER_PAGE
from corelib.consts import K_POST
from corelib.mc import cache
from corelib.db import PropsItem, rdb, db
from corelib.utils import (cached_property, is_numeric, trunc_utf8, incr_key)
from models.user import User
from models.like import LikeMixin
from models.comment import CommentMixin
from models.collect import CollectMixin
from models.exceptions import NotAllowedException

# post.title 通过title获取post对象 # noqa
MC_KEY_GET_BY_TITLE = 'core:Post:get_by_title(%s)'

# post.id 通过id获取post对应的tags
MC_KEY_TAGS = 'core:Post:tags(%s)'

# tag.name 通过name获取tag对象
MC_KEY_GET_BY_NAME = 'core:Tag:get_by_name(%s)'

# tag.id|tag.name， page 通过id或name获取post分页
MC_KEY_GET_POSTS_BY_TAG = 'core:PostTag:get_posts_by_tag(%s,%s)'

# tag.id|tag.name 通过id或name获取post的数量 # noqa
MC_KEY_GET_COUNT_BY_TAG = 'core:PostTag:get_post_count_by_tag(%s)'


class Post(CommentMixin, LikeMixin, CollectMixin, db.Model):
    __tablename__ = 'posts'
    author_id = db.Column(db.Integer)
    title = db.Column(db.String(128), default='')
    orig_url = db.Column(db.String(255), default='')
    can_comment = db.Column(db.Boolean, default=True)
    content = PropsItem('content', '')
    kind = K_POST

    __table_args__ = (
        db.Index('idx_title', title),  # noqa
        db.Index('idx_authorId', author_id))

    def url(self):
        return '/{}/{}/'.format(self.__class__.__name__.lower(), self.id)

    @classmethod
    @cache(MC_KEY_GET_BY_TITLE % ('{title}'))
    def get_by_title(cls, title):
        return cls.query.filter_by(title=title).first()

    @classmethod
    def get(cls, identifier):
        return super().get(identifier) if is_numeric(identifier) \
            else cls.get_by_title(identifier)

    @property
    @cache(MC_KEY_TAGS % ('{self.id}'))
    def tags(self):
        post_ids = PostTag.query.with_entities(PostTag.tag_id).\
            filter(PostTag.post_id == self.id).all()

        tags = Tag.query.filter(Tag.id.in_((id for id, in post_ids))).all()
        return tags

    @cached_property
    def abstract_content(self):
        return trunc_utf8(self.content, 100)

    @cached_property
    def author(self):
        return User.get(self.author_id)

    @classmethod
    def create_or_update(cls, **kwargs):
        """ 给爬虫使用，创建post """
        tags = kwargs.pop('tags', [])
        created, obj = super().create_or_update(**kwargs)
        if tags:
            PostTag.update_multi(obj.id, tags, [])

        if created:
            from handler.tasks import feed_post_to_followers
            feed_post_to_followers.delay(obj.id)
        return created, obj

    def update(self, **kwargs):
        rdb.delete(MC_KEY_GET_BY_TITLE % self.title)  # 注意，在更新前清除缓存
        super().update(**kwargs)

    def delete(self):
        super().delete()
        for pt in PostTag.query.filter_by(post_id=self.id):
            pt.delete()

        from handler.tasks import remove_post_from_feed
        remove_post_from_feed.delay(self.id, self.author_id)

    @cached_property
    def netloc(self):
        return urlparse(self.orig_url).netloc

    @classmethod
    def clear_mc(cls, target):
        rdb.delete(MC_KEY_GET_BY_TITLE % target.title)
        rdb.delete(MC_KEY_TAGS % target.id)

    @classmethod
    def __flush_delete_event__(cls, target):
        super().__flush_delete_event__(target)
        cls.clear_mc(target)


class Tag(db.Model):
    """ 原则上Tag一旦创建，则不能修改或删除 """
    __tablename__ = 'tags'
    name = db.Column(db.String(128), default='', unique=True)

    __table_args__ = (db.Index('idx_name', name), )

    @classmethod
    @cache(MC_KEY_GET_BY_NAME % ('{name}'))
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    def delete(self):
        raise NotAllowedException

    def update(self, **kwargs):
        raise NotAllowedException

    @classmethod
    def create(cls, **kwargs):
        name = kwargs.pop('name')
        kwargs['name'] = name.lower()
        return super().create(**kwargs)


class PostTag(db.Model):
    __tablename__ = 'post_tags'
    post_id = db.Column(db.Integer)
    tag_id = db.Column(db.Integer)

    __table_args__ = (
        db.Index('idx_post_id', post_id, 'updated_at'),
        db.Index('idx_tag_id', tag_id, 'updated_at'),
    )

    @classmethod
    def _get_posts_by_tag(cls, identifier):
        if not identifier:
            return
        if not is_numeric(identifier):
            tag = Tag.get_by_name(identifier)
            if not tag:
                return
            identifier = tag.id
        post_ids = cls.query.with_entities(
            cls.post_id).filter(cls.tag_id == identifier).all()

        query = Post.query.filter(Post.id.in_(
            id for id, in post_ids)).order_by(Post.id.desc())
        return query

    @classmethod
    @cache(MC_KEY_GET_POSTS_BY_TAG % ('{identifier}', '{page}'))
    def get_posts_by_tag(cls, identifier, page=1):
        """ `identifier`: tag_id or tag_name """
        query = cls._get_posts_by_tag(identifier)
        if not query:
            return []
        posts = query.paginate(page, PER_PAGE)
        del posts.query  # Fix `TypeError: can't pickle _thread.lock objects`
        return posts

    @classmethod
    @cache(MC_KEY_GET_COUNT_BY_TAG % ('{identifier}'))
    def get_post_count_by_tag(cls, identifier):
        """ identifier`: tag_id or tag_name """
        query = cls._get_posts_by_tag(identifier)
        return query.count() if query else 0

    @classmethod
    def update_multi(cls, post_id, tags, origin_tags=None):
        if origin_tags is None:
            origin_tags = Post.get(post_id).tags
        need_add = set(tags) - set(origin_tags)
        need_del = set(origin_tags) - set(tags)

        for tag_name in need_add:
            _, tag = Tag.create(name=tag_name)
            cls.create(post_id=post_id, tag_id=tag.id)

        for tag_name in need_del:
            _, tag = Tag.create(name=tag_name)
            obj = cls.query.filter_by(post_id=post_id, tag_id=tag.id).first()
            obj.delete()

    @classmethod
    def __flush_insert_event__(cls, target):
        super().__flush_insert_event__(target)
        cls.clear_mc(target, 1)

    @classmethod
    def __flush_delete_event__(cls, target):
        super().__flush_delete_event__(target)
        cls.clear_mc(target, -1)

    @classmethod
    def clear_mc(cls, target, amount):
        tag_id = target.tag_id
        tag_name = Tag.get(tag_id).name
        for ident in (tag_id, tag_name):
            total = incr_key(MC_KEY_GET_COUNT_BY_TAG % ident, amount)
            pages = math.ceil((max(total, 0) or 1) / PER_PAGE)
            for p in range(1, pages + 1):
                rdb.delete(MC_KEY_GET_POSTS_BY_TAG % (ident, p))
