import smtplib

from celery.utils.log import get_task_logger

from app import app as _app
from handler.celery import app
from corelib.consts import K_POST
from models.search import Item, TARGET_MAPPER
from models.core import Post
from models.feed import (
    feed_followed_posts_to_follower as _feed_followed_posts_to_follower,
    feed_post_to_followers as _feed_post_to_followers,
    remove_post_from_feed as _remove_post_from_feed,
    add_to_activity_feed as _add_to_activity_feed,
    remove_user_posts_from_feed as _remove_user_posts_from_feed)

logger = get_task_logger(__name__)


class RequestContextTask(app.Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        with _app.test_request_context():
            return super().__call__(*args, **kwargs)


@app.task
def send_email(smtp_host, from_addr, login_pwd, to_addrs, msg):
    s = smtplib.SMTP_SSL(smtp_host, port=465)
    s.login(from_addr, login_pwd)
    s.sendmail(from_addr, to_addrs, msg)
    s.quit()


@app.task(base=RequestContextTask)
def reindex(id, kind, op_type):
    target_cls = TARGET_MAPPER.get(kind)
    if not target_cls:
        logger.info(f'Reindex Error: Unexpected kind {kind}')
        return

    target = target_cls.get(id)

    if not target:
        logger.info(
            f'Reindex Error: Unexpected {target.__class__.__name__}<id={id}>'
        )  # noqa
        return
    logger.info(f'Reindex: {target.__class__.__name__}<id={id}>')
    if kind != K_POST:
        # 暂时不支持Post之外的类型
        return

    item = None

    if op_type == 'create':
        item = Item.add(target)
    elif op_type == 'update':
        item = Item.update_item(target)
    elif op_type == 'delete':
        item = Item.get(target.id, target.kind)
        Item.delete(item)
    if item:
        logger.info(f'Reindex Finished: {target.__class__.__name__}<id={id}>')
    else:
        logger.info(f'Reindex Failed: {target.__class__.__name__}<id={id}>')


@app.task(base=RequestContextTask)
def feed_followed_posts_to_follower(from_id, to_id):
    _feed_followed_posts_to_follower(from_id, to_id)
    logger.info(
        f'feed_followed_posts_to_follower from_to:{from_id}, uid:{to_id}')


@app.task(base=RequestContextTask)
def feed_post_to_followers(id):
    post = Post.get(id)
    _feed_post_to_followers(post)
    logger.info(f'feed_post_to_followers {id}')


@app.task(base=RequestContextTask)
def remove_post_from_feed(post_id, author_id):
    _remove_post_from_feed(post_id, author_id)
    logger.info(
        f'Remove_post_from_feed post_id:{post_id}, author_id: {author_id}')


@app.task(base=RequestContextTask)
def remove_user_posts_from_feed(visit_id, uid):
    _remove_user_posts_from_feed(visit_id, uid)
    logger.info(f'Remove_user_posts_from_feed visit_id:{visit_id}, uid:{uid}')


@app.task(base=RequestContextTask)
def add_to_activity_feed(post_id):
    _add_to_activity_feed(post_id)
    logger.info(f'Add_to_activity_feed post_id:{post_id}')
