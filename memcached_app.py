from core import app
import memcache
import json

mc = memcache.Client(['127.0.0.1:11211'], debug=False)

@app.session.register()
def set(key, val):
    sid = app.session.id

    session = mc.get(sid)
    session = json.loads(session or '{}')

    session[key] = val

    mc.set(sid, json.dumps(session))

@app.session.register()
def get(key, default=None):
    sid = app.session.id

    session = mc.get(sid)
    session = json.loads(session or '{}')

    if key is None:
        return session
    else:
        return session.get(key, default)

@app.session.register()
def delete():
    sid = app.session.id

    mc.delete(sid)

@app.session.register()
def exist():
    sid = app.session.id

    return bool(mc.get(sid))

@app.session.register('__repr__')
def __repr__():
    sid = self.id

    print "OK"

    session = mc.get(sid)

    return json.loads(session or '{}')