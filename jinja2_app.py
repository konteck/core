from core import app, view
from jinja2 import Environment, FileSystemLoader
import os

app = app(__name__)

view.env = Environment()

@app.view.register()
def render(file, args={}):
    envs = view.env.globals
    view.env = Environment()
    view.env.globals = envs
    view.env.loader = FileSystemLoader([os.path.dirname(file), os.path.dirname(os.path.dirname(file))]) # TODO Find better solution for nested templates

    template = view.env.get_template(os.path.basename(file))

    return template.render(args)
