from flask import Flask
from flask_sqlalchemy_lite import SQLAlchemy
from flask_caching import Cache
from flask_pymongo import PyMongo
from celery import Celery, Task


# Singletons
local_cache =   Cache()
mongo =         PyMongo()
db =            SQLAlchemy()

def celery_init_app(app: Flask) -> Celery:
    '''
    Celery worker set up for asynchronous workstream
    [Not in use in current design]
    '''
    # celery setup
    class ContextTask(Task):
        def __call__(self, *args: object, **kwargs: object):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery_app = Celery(app.name, task_cls=ContextTask)
    celery_app.config_from_object(app.config['CELERY_SETTINGS'])
    celery_app.set_default()
    app.extensions['celery'] = celery_app
    return celery_app