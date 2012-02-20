from core import app
import tornado.wsgi, tornado.ioloop, tornado.httpserver

app = app(__name__)

@app.register()
def run(port=8000):
    container = tornado.wsgi.WSGIContainer(app.WSGI())
    http_server = tornado.httpserver.HTTPServer(container)
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()

