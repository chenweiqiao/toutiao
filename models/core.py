import os
import math
from urllib.request import urlparse

from config import PER_PAGE
from corelib.consts import K_POST
from corelib.mc import cache
from corelib.db import PropsItem, rdb, db
from corelib.utils import (cached_hybrid_property, is_numeric, trunc_utf8,
                           incr_key)
from models.user import User
from models.like import LikeMixin
from models.comment import CommentMixin
from models.collect import CollectMixin
from models.exceptions import NotAllowedException

MC_KEY_POSTS_BY_TAG = 'core:posts_by_tags:%s:%s'  # tag.id|tag.name page
MC_KEY_POST_STATS_BY_TAG = 'core:count_by_tags:%s'  # tag.id|tag.name
MC_KEY_POST_TAGS = 'core:post:%s:tags'  # post.id

HERE = os.path.abspath(os.path.dirname(__file__))


class Post(CommentMixin, LikeMixin, CollectMixin, db.Model):
    __tablename__ = 'posts'
    author_id = db.Column(db.Integer)
    title = db.Column(db.String(128), default='')
    orig_url = db.Column(db.String(255), default='')
    can_comment = db.Column(db.Boolean, default=True)
    content = PropsItem('content', '')
    kind = K_POST

    __table_args__ = (
        db.Index('idx_title', title),
        db.Index('idx_authorId', author_id)
    )

    def url(self):
        return '/{}/{}/'.format(self.__class__.__name__.lower(), self.id)

    @classmethod
    def __flush_event__(cls, target):
        pass

    @classmethod
    def get(cls, identifier):
        return cls.cache.get(identifier) if is_numeric(identifier) \
            else cls.cache.filter(title=identifier).first()

    @property
    @cache(MC_KEY_POST_TAGS % ('{self.id}'))
    def tags(self):
        """ 获取post对应的tags """
        at_ids = PostTag.query.with_entities(
            PostTag.tag_id).filter(
                PostTag.post_id == self.id
            ).all()

        tags = Tag.query.filter(Tag.id.in_((id for id, in at_ids))).all()
        return tags

    @cached_hybrid_property
    def abstract_content(self):
        return trunc_utf8(self.content, 100)

    @cached_hybrid_property
    def author(self):
        return User.get(self.author_id)

    @classmethod
    def create_or_update(cls, **kwargs):
        """ 给爬虫使用，创建post """
        tags = kwargs.pop('tags', [])
        created, obj = super(Post, cls).create_or_update(**kwargs)
        if tags:
            PostTag.update_multi(obj.id, tags, [])

        if created:
            from handler.tasks import feed_post, reindex
            reindex.delay(obj.id, obj.kind, op_type='create')
            feed_post.delay(obj.id)
        return created, obj

    def delete(self):
        id = self.id
        super().delete()
        for pt in PostTag.query.filter_by(post_id=id):
            pt.delete()

        from handler.tasks import remove_post_from_feed
        remove_post_from_feed.delay(self.id, self.author_id)

    @cached_hybrid_property
    def netloc(self):
        return urlparse(self.orig_url).netloc

    @staticmethod
    def _flush_insert_event(mapper, connection, target):
        target._flush_event(mapper, connection, target)
        target.__flush_insert_event__(target)


class Tag(db.Model):
    __tablename__ = 'tags'
    name = db.Column(db.String(128), default='', unique=True)

    __table_args__ = (
        db.Index('idx_name', name),
    )

    @classmethod
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

    @classmethod
    def __flush_event__(cls, target):
        pass


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
            return []
        if not is_numeric(identifier):
            tag = Tag.get_by_name(identifier)
            if not tag:
                return
            identifier = tag.id
        at_ids = cls.query.with_entities(cls.post_id).filter(
            cls.tag_id == identifier
        ).all()

        query = Post.query.filter(
            Post.id.in_(id for id, in at_ids)).order_by(Post.id.desc())
        return query

    @classmethod
    @cache(MC_KEY_POSTS_BY_TAG % ('{identifier}', '{page}'))
    def get_posts_by_tag(cls, identifier, page=1):
        """
        获取与tag关联的所有post

        `identifier`: tag_id or tag_name
        """
        query = cls._get_posts_by_tag(identifier)
        posts = query.paginate(page, PER_PAGE)
        del posts.query  # Fix `TypeError: can't pickle _thread.lock objects`
        return posts

    @classmethod
    @cache(MC_KEY_POST_STATS_BY_TAG % ('{identifier}'))
    def get_count_by_tag(cls, identifier):
        """
        获取与tag关联的所有post数量

        `identifier`: tag_id or tag_name
        """
        query = cls._get_posts_by_tag(identifier)
        return query.count()

    @classmethod
    def update_multi(cls, post_id, tags, origin_tags=None):
        if origin_tags is None:
            origin_tags = Post.get(post_id).tags
        need_add = set(tags) - set(origin_tags)
        need_del = set(origin_tags) - set(tags)

        need_add_tag_ids = set()
        need_del_tag_ids = set()
        for tag_name in need_add:
            _, tag = Tag.create(name=tag_name)
            need_add_tag_ids.add(tag.id)

        for tag_name in need_del:
            _, tag = Tag.create(name=tag_name)
            need_del_tag_ids.add(tag.id)

        if need_del_tag_ids:
            obj = cls.query.filter(cls.post_id == post_id,
                                   cls.tag_id.in_(need_del_tag_ids))
            obj.delete(synchronize_session='fetch')  # 批量删除表记录，需要commit提交
            db.session.commit()

        for tag_id in need_add_tag_ids:
            cls.create(post_id=post_id, tag_id=tag_id)

    @staticmethod
    def _flush_insert_event(mapper, connection, target):
        super(PostTag, target)._flush_insert_event(mapper, connection, target)
        target.clear_mc(target, 1)

    @staticmethod
    def _flush_delete_event(mapper, connection, target):
        super(PostTag, target)._flush_delete_event(mapper, connection, target)
        target.clear_mc(target, -1)

    @staticmethod
    def _flush_after_update_event(mapper, connection, target):
        super(PostTag, target)._flush_after_update_event(
            mapper, connection, target)
        target.clear_mc(target, 1)

    @staticmethod
    def _flush_before_update_event(mapper, connection, target):
        super(PostTag, target)._flush_before_update_event(
            mapper, connection, target)
        target.clear_mc(target, -1)

    @staticmethod
    def clear_mc(target, amount):
        tag_id = target.tag_id
        tag_name = Tag.get(target.tag_id).name
        for ident in (tag_id, tag_name):
            total = incr_key(MC_KEY_POST_STATS_BY_TAG % ident, amount)
            pages = math.ceil((max(total, 0) or 1) / PER_PAGE)
            for p in range(1, pages + 1):
                rdb.delete(MC_KEY_POSTS_BY_TAG % (ident, p))
