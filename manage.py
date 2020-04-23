import os
from flask.cli import with_appcontext, click
from flask_migrate import Migrate

from app import app
from corelib.db import rdb, db
from models.search import Item


def include_object(object, name, type_, reflected, compare_to):
    if type_ == 'table' and name.startswith('social_auth'):
        return False
    return True


migrate = Migrate(app, db, include_object=include_object)
engine = db.get_engine(app)


def _flush_environ():
    engine.execute('DROP TABLE IF EXISTS `alembic_version`')
    db.drop_all()
    rdb.flushall()  # 销毁redis数据
    Item._index.delete(ignore=404)  # 删除Elasticsearch索引，销毁全部数据


def _create_environ():
    db.create_all()
    Item.init()


def _add_users():
    import datetime
    from models.user import User

    _, u1 = User.create(name='admin',
                        password='admin',
                        active=True,
                        confirmed_at=datetime.datetime.now())
    _, u2 = User.create(name='guest',
                        password='guest',
                        active=True,
                        confirmed_at=datetime.datetime.now())
    u1.follow(u2.id)  # u2 关注 u1，测试时用 u2 登录


def _crawl_posts():
    os.system('python3 crawling.py')


@app.cli.command('initdb', short_help='Inits testing environment.')
@with_appcontext
def reset_environ():
    _flush_environ()
    _create_environ()
    _add_users()
    _crawl_posts()

    print('\nInit Finished!\n')
    # os.system('celery worker -A handler.celery -l info')


@app.cli.command('ishell', short_help='Runs a IPython shell in the app context.')
@click.argument('ipython_args', nargs=-1, type=click.UNPROCESSED)
@with_appcontext
def ishell(ipython_args):
    import sys
    import IPython
    from IPython.terminal.ipapp import load_default_config
    from traitlets.config.loader import Config

    from models.user import User, Role
    from models.core import Post, Tag, PostTag
    from models.contact import Contact, userFollowStats

    if 'IPYTHON_CONFIG' in app.config:
        config = Config(app.config['IPYTHON_CONFIG'])
    else:
        config = load_default_config()

    user_ns = app.make_shell_context()
    user_ns.update(dict(db=db, User=User, Role=Role, rdb=rdb, Post=Post,
                        Tag=Tag, PostTag=PostTag, Item=Item, Contact=Contact,
                        userFollowStats=userFollowStats))
    config.TerminalInteractiveShell.banner1 = '''\
Python %s on %s
IPython: %s
App: %s%s
Instance: %s''' % (sys.version,
                   sys.platform,
                   IPython.__version__,
                   app.import_name,
                   app.debug and ' [debug]' or '',
                   app.instance_path)

    IPython.start_ipython(user_ns=user_ns, config=config, argv=ipython_args)
