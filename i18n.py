from core import app, config, view
import os, json

def locale(self, code):
    file_path = os.path.join(self.path, 'locales', code + '.json')

    if os.path.exists(file_path):
        arr = json.loads(open(file_path, 'r').read())
        app.locale.__globals__.update(arr)

    return self

app.locale = locale

def __(*args):
    if not args:
        return ''

    str = app.locale.__globals__.get(args[0], args[0])

    return str % args[1:]

view.env.globals.update(__=__)