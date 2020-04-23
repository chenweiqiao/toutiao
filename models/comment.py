from corelib.db import db

from models.actionmixin import ActionMixin
from models.like import LikeMixin
from models.user import User
from corelib.db import PropsItem
from corelib.consts import K_COMMENT
from corelib.utils import cached_property


class CommentItem(ActionMixin, LikeMixin, db.Model):
    __tablename__ = 'comment_items'
    user_id = db.Column(db.Integer)
    target_id = db.Column(db.Integer)
    target_kind = db.Column(db.Integer)
    ref_id = db.Column(db.Integer, default=0)  # 评论分文章评论，还有评论的评论，文章评论设置为0
    content = PropsItem()
    kind = K_COMMENT

    action_type = 'comment'

    __table_args__ = (db.Index('idx_ti_tk_ui', target_id, target_kind,
                               user_id), )

    @cached_property
    def html_content(self):
        return self.content

    @cached_property
    def user(self):
        return User.get(self.user_id)


class CommentMixin(object):
    def add_comment(self, user_id, content, ref_id=None):
        ok, obj = CommentItem.create(user_id=user_id,
                                     target_id=self.id,
                                     target_kind=self.kind,
                                     ref_id=ref_id)
        if ok:
            obj.content = content
        return ok, obj

    def del_comment(self, user_id, comment_id):
        comment = CommentItem.get(comment_id)
        if comment and comment.user_id == user_id and \
           comment.target_id == self.id and comment.target_kind == self.kind:
            comment.delete()
            return True
        return False

    def get_comments(self, page):
        return CommentItem.get_page_by_target(self.id, self.kind, page)

    @property
    def n_comments(self):
        return int(CommentItem.get_count_by_target(self.id, self.kind))
