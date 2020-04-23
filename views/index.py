import os

from flask import render_template, send_from_directory, abort, request
from flask.blueprints import Blueprint
from flask_security import login_required

from models.core import Post, Tag, PostTag
from models.search import Item
from models.feed import get_user_feed
from config import UPLOAD_FOLDER

bp = Blueprint('index', __name__)


@bp.route('/')
@login_required
def index():
    page = request.args.get('page', default=1, type=int)
    posts = get_user_feed(request.user_id, page)
    return render_template('index.html', posts=posts, page=page)


@bp.route('/post/<id>/')
def post(id):
    post = Post.get_or_404(id)
    return render_template('post.html', post=post)


@bp.route('/static/avatars/<path>')
def avatar(path):
    return send_from_directory(os.path.join(UPLOAD_FOLDER, 'avatars'), path)


@bp.route('/tag/<ident>/')  # 这个`ident`在页面代码中被固定为`python`，爬虫爬取的post手动新添一个`python`标签 # noqa
def tag(ident):
    ident = ident.lower()
    tag = Tag.get_by_name(ident)
    if not tag:
        tag = Tag.get(ident)
        if not tag:
            abort(404)
    page = request.args.get('page', default=1, type=int)
    type = request.args.get('type', default='hot')  # hot/latest
    if type == 'latest':
        posts = PostTag.get_posts_by_tag(ident, page)
    elif type == 'hot':
        posts = Item.get_post_ids_by_tag(ident, page, type)  # 从Elasticsearch中查找 # noqa
        posts.items = Post.get_multi(posts.items)
    else:
        # 未知类型
        posts = []
    return render_template('tag.html', tag=tag, ident=ident, posts=posts,
                           type=type)  # 模板能忽略post类型的错误，即使传入posts=[]


@bp.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', default=1, type=int)
    posts = Item.new_search(query, page)
    return render_template('search.html', query=query, posts=posts)
