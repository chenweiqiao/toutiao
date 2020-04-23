import os
from flask_security import UserMixin, RoleMixin

import requests

from corelib.db import db
from config import UPLOAD_FOLDER
from corelib.utils import generate_id
from models.contact import Contact, userFollowStats

roles_users = db.Table(
    'roles_users',  # noqa
    db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(RoleMixin, db.Model):
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(191))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    bio = db.Column(db.String(128), default='')
    name = db.Column(db.String(128), default='')
    nickname = db.Column(db.String(128), default='')
    email = db.Column(db.String(191), default='')
    password = db.Column(db.String(191))
    website = db.Column(db.String(191), default='')
    github_url = db.Column(db.String(191), default='')
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    active = db.Column(db.Boolean())
    icon_color = db.Column(db.String(7))
    confirmed_at = db.Column(db.DateTime())
    company = db.Column(db.String(191), default='')
    avatar_id = db.Column(db.String(20), default='')
    roles = db.relationship('Role',
                            secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    __table_args__ = (
        db.Index('idx_name', name),
        db.Index('idx_email', email),
    )

    def url(self):
        return '/user/{}'.format(self.id)

    @property
    def github_id(self):
        return self.github_url.split('/')[-1]

    @property
    def avatar_path(self):
        avatar_id = self.avatar_id
        return '' if not avatar_id else '/static/avatars/{}.png'.format(
            avatar_id)

    def update_avatar(self, avatar_id):
        self.avatar_id = avatar_id
        self.save()

    def upload_avatar(self, img):
        avatar_id = generate_id()
        filename = os.path.join(UPLOAD_FOLDER, 'avatars',
                                '{}.png'.format(avatar_id))

        if isinstance(img, str) and img.startswith('http'):
            r = requests.get(img, stream=True)
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
        else:
            img.save(filename)
        self.update_avatar(avatar_id)

    def follow(self, from_id):
        ok, _ = Contact.create(to_id=self.id, from_id=from_id)
        return ok

    def unfollow(self, from_id):
        contact = Contact.get_follow_item(from_id, self.id)
        if contact:
            contact.delete()
        return True if contact else False

    def is_followed_by(self, user_id):
        contact = Contact.get_follow_item(user_id, self.id)
        return bool(contact)

    @property
    def n_following(self):
        return self._follow_stats[1]

    @property
    def n_followers(self):
        return self._follow_stats[0]

    @property
    def _follow_stats(self):
        stats = userFollowStats.get(self.id)
        return (stats.follower_count, stats.following_count) if stats else (0, 0)  # noqa

    def delete(self):
        from models.like import LikeItem
        from models.collect import CollectItem
        from models.comment import CommentItem

        super().delete()
        for cond in (Contact.from_id, Contact.to_id):
            for contact in Contact.query.filter(cond == self.id):
                contact.delete()  # 注意，放在sqlalchemy的清理钩子里，会报错

        for cls_type in (LikeItem, CollectItem, CommentItem):
            for like in cls_type.query.filter_by(user_id=self.id):
                like.delete()
