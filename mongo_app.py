from core import app
from mongoengine import *
from datetime import datetime

@app.session.register()
def set(key, val):
    sid = app.session.id

    s = Sessions.objects.get_or_create(sid=sid, defaults={'data': {}})[0]
    s.data[key] = val
    s.save()

@app.session.register()
def get(key, default=None):
    sid = app.session.id

    s = Sessions.objects.get_or_create(sid=sid, defaults={'data': {}})[0]

    if key is not None:
        return s.data.get(key, default)
    else:
        return s.data

@app.session.register()
def delete():
    sid = app.session.id

    app.cookies('SID', '')
    Sessions.objects(sid=sid).delete()

@app.session.register()
def exist():
    sid = app.session.id

    return bool(Sessions.objects(sid=sid))

@app.session.register('__repr__')
def __repr__():
    sid = app.session.id

    return Sessions.objects.get_or_create(sid=sid, defaults={'data': {}})[0]

@app.log.register()
def error(e):
    import traceback

    if issubclass(e.__class__, Exception):
        e = e.message

    Logs(level='error', message=e, trace=traceback.format_exc()).save()

    print(e)

class Sessions(Document):
    sid = StringField(max_length=32, required=True)
    data = DictField()
    create_date = DateTimeField(default=datetime.now)

class Logs(Document):
    level = StringField(max_length=10, required=True)
    message = StringField()
    trace = StringField()
    create_date = DateTimeField(default=datetime.now)