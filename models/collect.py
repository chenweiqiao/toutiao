from corelib.db import db
from models.actionmixin import ActionMixin


class CollectItem(ActionMixin, db.Model):
    __tablename__ = 'collect_items'
    user_id = db.Column(db.Integer)
    target_id = db.Column(db.Integer)
    target_kind = db.Column(db.Integer)

    # 根据action_type判断相似功能的类, 如CommentItem, LikeItem
    action_type = 'collect'

    __table_args__ = (db.Index('idx_ti_tk_ui', target_id, target_kind,
                               user_id), )


class CollectMixin:
    def collect(self, user_id):
        item = CollectItem.get_by_target(user_id, self.id, self.kind)
        if item:
            return False
        ok, _ = CollectItem.create(user_id=user_id,
                                   target_id=self.id,
                                   target_kind=self.kind)
        return ok

    def uncollect(self, user_id):
        item = CollectItem.get_by_target(user_id, self.id, self.kind)
        if item:
            item.delete()
            return True
        return False

    @property
    def n_collects(self):
        return int(CollectItem.get_count_by_target(self.id, self.kind))

    def is_collected_by(self, user_id):
        return bool(CollectItem.get_by_target(user_id, self.id, self.kind))
