TEMPLATES_AUTO_RELOAD = True
FROM_USER = 'xxx@qq.com'
EXMAIL_PASSWORD = 'xxxxxx'
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123@localhost/toutiao?charset=utf8mb4'  # noqa 
BROKER_URL = 'pyamqp://chenvq:123456@localhost:5672/toutiao'  # 使用RabbitMQ作为消息代理 # noqa
SOCIAL_AUTH_GITHUB_KEY = ''
SOCIAL_AUTH_GITHUB_SECRET = ''
