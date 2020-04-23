from flask import request, get_template_attribute
from flask.views import MethodView

from ext import db, security, user_datastore
from models.core import Post
from models.user import User
from . import errors
from .utils import ApiResult, marshal_with, ApiFlask
from .exceptions import ApiException
from .schemas import PostSchema, AuthorSchema


def create_app():
    app = ApiFlask(__name__, template_folder='../../templates')  # 以当前app模块所在路径开始计算模板文件夹所在路径 # noqa
    app.config.from_object('config')  # 但加载`config.py`却是在程序开始运行处
    db.init_app(app)
    security.init_app(app, user_datastore)

    return app


json_api = create_app()


@json_api.errorhandler(ApiException)
def api_error_handler(error):
    return error.to_result()  # return ApiResult obj


@json_api.errorhandler(401)
@json_api.errorhandler(403)
@json_api.errorhandler(404)
@json_api.errorhandler(500)
def error_handler(error):
    if hasattr(error, 'name'):
        status = error.code
        if status == 403:
            msg = '无权限'
        else:
            msg = error.name
    else:
        msg = error.message
        status = 500
    return ApiResult({'errmsg': msg, 'r': 1, 'status': status})


class ActionAPI(MethodView):
    """ ActionAPI for `LikeItem` | `CollectItem` | `CommentItem` """
    do_action = None
    undo_action = None

    def _prepare(self, post_id):
        post = Post.query.get(post_id)
        if not post:
            raise ApiException(errors.post_not_found)
        return post

    def _merge(self, post):
        user_id = request.user_id
        post.is_liked = post.is_liked_by(user_id)
        post.is_collected = post.is_collected_by(user_id)
        return post

    @marshal_with(PostSchema)
    def post(self, post_id):
        post = self._prepare(post_id)
        if self.do_action != 'add_comment':
            ok = getattr(post, self.do_action)(request.user_id)
        else:
            # 没有验证字段，存在漏洞 :<
            content = request.form.get('content')
            ok, comment = getattr(post, self.do_action)(request.user_id,
                                                        content)
            if ok:
                macro = get_template_attribute('_macros.html',
                                               'render_comment')
                return {'html': str(macro(comment).replace('\n\r', ''))} # CRLF行尾合并多行为一行 # noqa
        if not ok:
            raise ApiException(errors.illegal_state)
        return self._merge(post)

    @marshal_with(PostSchema)
    def delete(self, post_id):
        post = self._prepare(post_id)
        if self.do_action != 'del_comment':
            ok = getattr(post, self.undo_action)(request.user_id)
        else:
            comment_id = request.form.get('comment_id')
            ok = getattr(post, self.undo_action)(request.user_id, comment_id)
        if not ok:
            raise ApiException(errors.illegal_state)
        return self._merge(post)


class LikeAPI(ActionAPI):
    do_action = 'like'
    undo_action = 'unlike'


class CommentAPI(ActionAPI):
    do_action = 'add_comment'
    undo_action = 'del_comment'


class CollectAPI(ActionAPI):
    do_action = 'collect'
    undo_action = 'uncollect'


class FollowAPI(MethodView):
    def _prepare(self, user_id):
        user = User.get(user_id)
        if not user:
            raise ApiException(errors.not_found)
        return user

    def _merge(self, user):
        user.is_followed = user.is_followed_by(request.user_id)
        return user

    @marshal_with(AuthorSchema)
    def post(self, user_id):
        user = self._prepare(user_id)
        ok = user.follow(request.user_id)
        if not ok:
            raise ApiException(errors.illegal_state)
        return self._merge(user)

    @marshal_with(AuthorSchema)
    def delete(self, user_id):
        user = self._prepare(user_id)
        ok = user.unfollow(request.user_id)
        if not ok:
            raise ApiException(errors.illegal_state)
        return self._merge(user)


for name, view_cls in (('like', LikeAPI), ('comment', CommentAPI),
                       ('collect', CollectAPI)):
    view = view_cls.as_view(name)
    json_api.add_url_rule(f'/post/<int:post_id>/{name}',
                          view_func=view,
                          methods=['POST', 'DELETE'])

follow_view = FollowAPI.as_view('follow')
json_api.add_url_rule('/user/<int:user_id>/follow',
                      view_func=follow_view,
                      methods=['POST', 'DELETE'])


from . import authentication  # 避免循环引用 # noqa
