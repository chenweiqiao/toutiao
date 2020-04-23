"""
注意，下面的函数参数，参考`Contact`模型里的字段定义, `from_id`为关注者`follower`，
`to_id`为被关注者`followed`。

热门分享feed流-`ACTIVITY_KEY`
1. 当文章点赞数超过阈值`HOT_THRESHOLD`时， 它就会被放入热门分享的feed流里， 供所有用户查看；
2. 一段时间后，热门文章会合并到关注者的feed流中，这个动作是由关注者自己产生。

关注者`follower`的feed流-`FEED_KEY`
1. 每个关注者`follower`都有自己的feed流；
2. 当关注者`follower`关注了某人`followed`后，会把某人的所有文章放入到用户自己的feed流；
2.2 文章可以有期限，例如300天内（适用于第一次关注），也可以从上次阅读时间到现在（适用于取消再关注）；
3. 被关注者`followed`新发表一篇文章，他的关注者`followers`都会把文章放入自己的feed流；
4. 加到feed流时，记录当前的最新的文章ID，作为书签，供以后取消再关注使用，读取书签以后的新文章
"""

import math
from datetime import datetime, timedelta

from flask_sqlalchemy import Pagination

from config import PER_PAGE
from models.user import User
from models.core import Post
from models.contact import Contact
from corelib.consts import ONE_MINUTE
from corelib.db import rdb

DAYS = 300  # 300天内的文章
MAX = 100

# from_id 关注者`follower`的feed流，放入各种感兴趣的文章
FEED_KEY = 'feed:{}'

# 热门分享，只保留100个，它面向所有用户
ACTIVITY_KEY = 'feed:activity'

# from_id 热门分享feed流的有效标记，标记失效后会从热门分享重新拉取热门文章合并到关注者的feed流中
ACTIVITY_UPDATED_KEY = 'feed:activity_updated:{}'

# to_id:from_id 文章加入到关注者feed流后，会记录文章ID作为已阅读的书签，它适用于取消再关注的场景
LAST_VISIT_KEY = 'feed:last_visit_id:{}:{}'


class ActivityFeed:
    @staticmethod
    def add(time, post_id):
        rdb.zadd(ACTIVITY_KEY, {post_id: -time})  # Fix mapping
        rdb.zremrangebyrank(ACTIVITY_KEY, MAX, -1)  # 只保留前100个热门文章

    @staticmethod
    def delete(*post_ids):
        if post_ids:
            rdb.zrem(ACTIVITY_KEY, *post_ids)

    @staticmethod
    def get_all():
        return rdb.zrange(ACTIVITY_KEY, 0, -1, withscores=True)


def get_followed_latest_posts(to_id, from_id):
    user = User.get(to_id)
    if not user:
        return

    query = Post.query.with_entities(Post.id, Post.created_at).filter(Post.author_id == to_id)  # noqa
    visit_key = LAST_VISIT_KEY.format(to_id, from_id)
    last_visit_id = rdb.get(visit_key)
    if last_visit_id:
        query = query.filter(Post.id > int(last_visit_id))
    else:
        query = query.filter(Post.created_at >= (datetime.now() - timedelta(days=DAYS)))  # noqa

    posts = query.order_by(Post.id.desc()).all()

    if posts:
        last_visit_id = posts[0][0]
        rdb.set(visit_key, last_visit_id)
    return posts


def gen_followers(to_id):
    user = User.get(to_id)
    if not user:
        return []

    pages = math.ceil((max(user.n_followers, 0) or 1) / PER_PAGE)
    for p in range(1, pages + 1):
        yield Contact.get_followers_paginate(to_id, p).items


def feed_followed_posts_to_follower(from_id, to_id):
    """ 把被关注者`to_id`的文章放入到关注者`from_id`的`FEED_KEY`流中 """
    posts = get_followed_latest_posts(to_id, from_id)
    if not posts:
        return
    items = {post_id: -int(created_at.timestamp()) for post_id, created_at in posts}  # noqa
    feed_key = FEED_KEY.format(from_id)
    rdb.zadd(feed_key, items)


def feed_post_to_followers(post):
    """ 把文章放入到所有关注了该文章作者的关注者的`FEED_KEY`流中 """
    to_user = User.get(post.author_id)
    for from_ids in gen_followers(post.author_id):
        for from_id in from_ids:
            feed_key = FEED_KEY.format(from_id)
            rdb.zadd(feed_key, {post.id: -int(post.created_at.strftime('%s'))})
            visit_key = LAST_VISIT_KEY.format(to_user.id, from_id)
            rdb.set(visit_key, post.id)


def remove_post_from_feed(post_id, author_id):
    """ 删除文章后，也要删除关注者的`FEED_KEY`里对应的文章ID """
    for from_ids in gen_followers(author_id):
        for from_id in from_ids:
            feed_key = FEED_KEY.format(from_id)
            rdb.zrem(feed_key, post_id)
            ActivityFeed.delete(post_id)


def remove_user_posts_from_feed(from_id, to_id):
    """ 取消关注后，也要删除关注者的`FEED_KEY`里所有该作者的文章ID """
    post_ids = [id for id, in Post.query.with_entities(Post.id).filter(
        Post.author_id == to_id)]
    feed_key = FEED_KEY.format(from_id)
    if post_ids:
        rdb.zrem(feed_key, *post_ids)


def get_user_feed(from_id, page):
    """ 获取用户的`FEED_KEY`的文章 """
    feed_key = FEED_KEY.format(from_id)
    update_key = ACTIVITY_UPDATED_KEY.format(from_id)
    if not rdb.get(update_key):
        items = ActivityFeed.get_all()
        if items:
            rdb.zadd(feed_key, dict(items))
        rdb.set(update_key, 1, ex=ONE_MINUTE * 5)
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE - 1
    post_ids = rdb.zrange(feed_key, start, end)
    items = Post.get_multi([int(id) for id in post_ids])
    total = rdb.zcard(feed_key)
    return Pagination(None, page, PER_PAGE, total, items)


def add_to_activity_feed(post_id):
    """ 把热门文章加入到`ACTIVITY_KEY`流中 """
    post = Post.get(post_id)
    ActivityFeed.add(int(post.created_at.timestamp()), post_id)
