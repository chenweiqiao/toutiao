from walrus import Database

from config import REDIS_URL

rdb = Database.from_url(REDIS_URL)
