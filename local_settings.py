FROM_USER = 'your_name@qq.com'
EXMAIL_PASSWORD = 'your_password'
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:password@localhost/toutiao?charset=utf8mb4'  # noqa 
BROKER_URL = 'pyamqp://user:password@localhost:5672/toutiao'  # 使用RabbitMQ作为消息代理 # noqa
