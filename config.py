import os

# Flask
SECRET_KEY = '123'
TEMPLATES_AUTO_RELOAD = True
PRESERVE_CONTEXT_ON_EXCEPTION = True  # catch exception in @teardown_request

# Extended Flask-SQLAlchemy
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/video?charset=utf8mb4'  # noqa
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_RECORD_QUERIES = False  # `debug:on`模式下总能启动`get_debug_queries`, 而只有True时`debug:off`模式才会启用`get_debug_queries`  # noqa

# Extended Flask-Security configuration
SECURITY_CONFIRMABLE = True
SECURITY_REGISTERABLE = True
SECURITY_RECOVERABLE = True
SECURITY_CHANGEABLE = True
SECURITY_TRACKABLE = True
SECURITY_POST_REGISTER_VIEW = SECURITY_POST_RESET_VIEW = SECURITY_POST_CONFIRM_VIEW = 'account.landing'  # 传给定制flask-security # noqa
SECURITY_PASSWORD_SALT = '234'
SECURITY_EMAIL_SUBJECT_CONFIRM = '请确认邮件 -  头条'
SECURITY_EMAIL_SUBJECT_REGISTER = '欢迎 - 头条'
SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = '重置密码 - 头条'
SECURITY_EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE = '密码已改变 - 头条'
SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = '密码已被重置 - 头条'
SECURITY_CONFIRM_EMAIL_WITHIN = SECURITY_RESET_PASSWORD_WITHIN = '6 hours'

# Extented Flask-Security messages
SECURITY_MSG_UNAUTHORIZED = ('你没有权限访问这个资源', 'error')
SECURITY_MSG_PASSWORD_MISMATCH = ('密码不匹配', 'error')
SECURITY_MSG_PASSWORD_RESET_EXPIRED = ((
    'You did not reset your password within %(within)s. '
    'New instructions have been sent to %(email)s.'), 'error')
SECURITY_MSG_DISABLED_ACCOUNT = ('账号被禁用了.', 'error')
SECURITY_MSG_INVALID_EMAIL_ADDRESS = ('邮箱地址错误', 'error')
SECURITY_MSG_PASSWORD_INVALID_LENGTH = ('错误的密码长度', 'error')
SECURITY_MSG_PASSWORD_IS_THE_SAME = ('新密码要和旧密码不一致', 'error')
SECURITY_MSG_EMAIL_NOT_PROVIDED = ('需要填写邮箱地址', 'error')
SECURITY_MSG_ALREADY_CONFIRMED = ('邮箱已经被确认', 'info')
SECURITY_MSG_PASSWORD_NOT_PROVIDED = ('需要输入密码', 'error')
SECURITY_MSG_USER_DOES_NOT_EXIST = ('用户不存在或者密码错误', 'error')
SECURITY_MSG_EMAIL_ALREADY_ASSOCIATED = ('%(email)s 已经被关联了', 'error')
SECURITY_MSG_CONFIRMATION_REQUIRED = ('登录前请先邮箱确认', 'error')
SECURITY_MSG_INVALID_PASSWORD = ('账号或者密码错误', 'error')
SECURITY_MSG_RETYPE_PASSWORD_MISMATCH = ('2次密码输入不一致', 'error')
SECURITY_USER_IDENTITY_ATTRIBUTES = ('email', 'name')

# Celery configuration
BROKER_URL = 'pyamqp://guest:123456@localhost:5672/test'  # 使用RabbitMQ作为消息代理
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # 把任务结果存在了Redis
CELERY_TASK_SERIALIZER = 'msgpack'  # 任务序列化和反序列化使用msgpack方案
CELERY_RESULT_SERIALIZER = 'json'  # 读取任务结果一般性能要求不高，所以使用了可读性更好的JSON
CELERY_TASK_RESULT_EXPIRES = 60 * 60 * 24  # 任务过期时间，不建议直接写86400，应该让这样的magic数字表述更明显 # noqa
CELERY_ACCEPT_CONTENT = ['json', 'msgpack']  # 指定接受的内容类型

# Email
SMTP_HOST = 'smtp.qq.com'
FROM_USER = 'no-reply@qq.com'
EXMAIL_PASSWORD = 'xxxxxxxx'  # SMTP服务密钥

REDIS_URL = 'redis://localhost:6379'

ES_HOSTS = ['localhost']

PER_PAGE = 2

HERE = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(HERE, 'permdir')
if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

try:
    from local_settings import *  # 引入本地设置  # noqa
except ImportError:
    pass
