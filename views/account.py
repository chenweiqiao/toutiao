# coding=utf-8

from flask import request, abort, render_template
from flask.blueprints import Blueprint
from flask_security import login_required

from models.user import User
from models.core import Post
from models.like import LikeItem
from models.collect import CollectItem
from models.contact import Contact
from corelib.utils import AttrDict

bp = Blueprint('account', __name__)


@bp.route('landing')
def landing():
    type = request.args.get('type')
    type_map = {
        'reset': '重置',
        'confirm': '确认',
        'register': '激活',
        'confirmed': '已确认'
    }
    email = request.args.get('email')
    if not email:
        abort(404)
    if type not in type_map:
        type = 'register'
    action = type_map.get(type)
    return render_template('security/landing.html', **locals())


@bp.route('settings/', methods=['GET', 'POST'])
@login_required
def settings():
    notice = False
    if request.method == 'POST':
        user = request.user
        image = request.files.get('user_image')
        d = request.form.to_dict()
        d.pop('submit', None)
        form = AttrDict(d)
        github_id = form.github_id
        if github_id:
            form.github_url = f'https://github.com/{github_id}'
        del form.github_id
        user.update(**form)
        if image:
            user.upload_avatar(image)
        notice = True
    return render_template('settings.html', notice=notice)


# yapf: disable
@bp.route('user/<identifier>/likes/')
def user_likes(identifier):
    return render_user_page(identifier, 'card.html', Post, 'like',
                            endpoint='account.user_likes')  # Fix pagination


@bp.route('user/<identifier>/favorites/')
def user_favorites(identifier):
    return render_user_page(identifier, 'card.html', Post, 'collect',
                            endpoint='account.user_favorites')


@bp.route('user/<identifier>/following/')
def user_following(identifier):
    return render_user_page(identifier, 'user.html', User, 'following',
                            endpoint='account.user_following')


@bp.route('user/<identifier>/followers/')
def user_followers(identifier):
    return render_user_page(identifier, 'user.html', User, 'followers',
                            endpoint='account.user_followers')


@bp.route('user/<identifier>/')
def user(identifier):
    return render_user_page(identifier, 'user.html', User,
                            endpoint='account.user')


def render_user_page(identifier, renderer, target_cls, type='following',
                     endpoint=None):
    user = User.get(identifier)
    if not user:
        abort(404)
    page = request.args.get('page', default=1, type=int)
    if type == 'collect':
        p = CollectItem.get_paginate_by_user(user.id, page=page)
    elif type == 'like':
        p = LikeItem.get_paginate_by_user(user.id, page=page)
    elif type == 'following':
        p = Contact.get_following_paginate(user.id, page=page)
    elif type == 'followers':
        p = Contact.get_followers_paginate(user.id, page=page)
    p.items = target_cls.get_multi(p.items)
    return render_template(renderer, **locals())
# yapf: enable
