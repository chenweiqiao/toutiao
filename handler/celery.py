from celery import Celery

app = Celery('handler', include=['handler.tasks'])
app.config_from_object('config')
