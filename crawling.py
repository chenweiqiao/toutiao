from datetime import datetime
from html.parser import HTMLParser

import feedparser

from app import app
from models.core import Post, PostTag, Tag, db
from models.search import Item
from models.collect import CollectItem
from models.comment import CommentItem
from models.like import LikeItem


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def fetch(url):
    d = feedparser.parse(url)
    entries = d.entries

    for entry in entries:
        try:
            content = entry.content and entry.content[0].value
        except AttributeError:
            content = entry.summary or entry.title
        try:
            created_at = datetime.strptime(entry.published,
                                           '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            created_at = datetime.strptime(entry.published,
                                           '%a, %d %b %Y %H:%M:%S %z')
        try:
            tags = entry.tags
        except AttributeError:
            tags = []

        ok, post = Post.create_or_update(author_id=1,
                                         title=entry.title,
                                         orig_url=entry.link,
                                         content=strip_tags(content),
                                         created_at=created_at,
                                         tags=[tag.term for tag in tags])


def main():
    with app.test_request_context():
        Item._index.delete(ignore=404)  # 删除Elasticsearch索引，销毁全部数据
        Item.init()
        for model in (Post, Tag, PostTag, CollectItem, CommentItem, LikeItem):
            model.query.delete()  # 数据库操作要通过SQLAlchemy，不要直接链接数据库操作
        db.session.commit()

        for site in ('https://coolshell.cn/feed', ):
            fetch(site)


if __name__ == '__main__':
    main()
