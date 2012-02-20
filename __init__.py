import os, sys, time, re
from Cookie import SimpleCookie

try: # AppEngine trick
    from urlparse import parse_qsl
except ImportError: # pragma: no cover
    from cgi import parse_qsl

try: # AppEngine trick
    import json
except ImportError: # pragma: no cover
    from django.utils import simplejson as json

# Try to run on interpritators new version
PY3 = True if sys.version_info >= (3, 0) else False

# TODO Fix for GAE
if PY3:
    from imp import reload

    def execfile(file, globals=globals(), locals=locals()):
        with open(file, "r") as fh:
            exec(fh.read() + "\n", globals, locals)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

HTTP_STATUS_CODES = {
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: 'I\'m a teapot',
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',
    449: 'Retry With',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended'
}

CONTENT_TO_COMPRESS = [
    'text/html',
    'text/css',
    'application/x-javascript'
]

SYSTEM_PAGE_TEMPLATE = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>%(title)s</title>
            <style>
               * { margin: 0; padding: 0; }
               h1 { color: #aaa; font-size: 60px; -moz-transform: rotate(270deg) translate(197px, -435px); -webkit-transform: rotate(270deg) translate(197px, -435px); transform: rotate(270deg) translate(197px, -435px); -o-transform: rotate(270deg) translate(197px, -435px); filter:progid:DXImageTransform.Microsoft.BasicImage(rotation=3); }
               h3:first-letter { color: #73A1C2; }
               h2 { color: #74a2c2; font-size: 30px; font-family: sans-serif; }
               h3 { color: #aaa; font-size: 20px; text-align: right; }
               pre { margin: 10px auto; padding: 10px; color: #000; overflow: auto; }
               div { margin: 10%% auto; width: 50%%; }
               hr { display: block; height: 1px; border: 0; border-top: 1px solid #74a2c2; margin: 1em 0; padding: 0; }
               i { float:right; }
            </style>
        </head>
        <body>
              <div>
              <h1>%(h1)s</h1>
              <h2>%(h2)s</h2>
              <h3>%(title)s</h3>
              <hr />
              <pre>%(message)s</pre>
              <hr />
              <i>ExCore</i>
              </div>
        </body>
        </html>
        """

# Helper functions
def array2xml(struct, file_name=None, root_tag='root', item_tag='item', encoding='utf-8', parent=None):
    import xml.etree.ElementTree as ET

    # build a tree structure
    if parent is None and root_tag is not None:
        parent = ET.Element(root_tag)

    if isinstance(struct, list):
        for item in struct:
            el = ET.SubElement(parent, item_tag)

            array2xml(item, root_tag=None, parent=el)
    elif isinstance(struct, dict):
        for node_name, node_val in struct.items():
            el = ET.SubElement(parent, node_name)

            if isinstance(node_val, (dict, list)):
                array2xml(node_val, root_tag=None, parent=el)
            else:
                el.text = str('null' if node_val is None else node_val)
    else:
        parent.text = str('null' if struct is None else struct)

    if file_name is not None:
        ET.ElementTree(parent).write(file_name, encoding=encoding)
        return True
    else:
        return ET.tostring(parent, encoding=encoding)

def xml2array(xml_string=None, file_name=None, parent=None, dict={}):
    import xml.etree.ElementTree as ET

    if parent is None:
        if xml_string:
            parent = ET.fromstring(xml_string)
        else:
            parent = ET.parse(file_name).getroot()

    if len(parent) == 0:
        return parent.text

    for node in parent:
        dict[node.tag] = xml2array(parent=node, dict={})

    return dict

class Hashmap(dict):
    def __init__(self, list={}, **kwds):
        self.update(list)
        self.update(kwds)

    def __new__(cls, *args, **kwargs):
        self = dict.__new__(cls, *args, **kwargs)
        self.__dict__ = self
        return self

    def __iter__(self):
        return self.iteritems()

    def __getattr__(self, name):
        return self.get(name, None)

    def set(self, name, value):
        self.__setitem__(name, value)

        return value

class Request(dict):
    scheme = None
    path = None
    method = None
    host = None
    ip = None
    port = None
    agent = None
    ajax = None
    type = None

    def bind(self, environ):
        self.update(environ)
        self.path = '/' + self.get('PATH_INFO', '/').lstrip('/')
        self.method = self.get('REQUEST_METHOD', 'GET').upper()
        self.host = self.get('HTTP_HOST', '').split(':')[0]
        self.scheme = self.get('wsgi.url_scheme', 'http').lower()
        self.ip = self.get('REMOTE_ADDR', '')
        self.port = self.get('SERVER_PORT', 80)
        self.agent = self.get('HTTP_USER_AGENT', '')
        self.type = self.get('CONTENT_TYPE', '')
        self.ajax = True if 'HTTP_X_REQUESTED_WITH' in self else False

    @property
    def GET(self):
        if 'CORE_GET' not in self:
            class Get(Hashmap):
                def __call__(self, rule=None, subdomain=None, handler=None):
                    def wrapper(func):
                        app.route(rule=rule, methods='GET', subdomain=subdomain, handler=func)

                        return func

                    if handler is not None:
                        wrapper(handler)

                    return wrapper

            data = parse_qsl(self.get('QUERY_STRING', ''), keep_blank_values=True)

            self['CORE_GET'] = Get(data)

        return self['CORE_GET']

    @property
    def POST(self):
        if 'CORE_POST' not in self:
        #            class Post(Hashmap):
        #                def __call__(self, rule=None, subdomain=None, handler=None):
        #                    def wrapper(func):
        #                        app.route(rule=rule, methods='POST', subdomain=subdomain, handler=func)
        #
        #                        return func
        #
        #                    if handler is not None:
        #                        wrapper(handler)
        #
        #                    return wrapper
        #
        #            if self.method == 'POST':
        #                data = parse_qsl(self.BODY, keep_blank_values=True)
        #            else:
        #                data = {}
        #
            safe_env = {
                'QUERY_STRING': ''
            }

            for key in ('REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
                if key in self:
                    safe_env[key] = self[key]

            from cgi import FieldStorage

            data = FieldStorage(fp=self.BODY, environ=safe_env, keep_blank_values=True)

            post = Hashmap()

            for val in data.list or []:
                post[val.name] = val if val.filename else val.value.decode('utf-8')

            self['CORE_POST'] = post

        return self['CORE_POST']

    @property
    def COOKIES(self):
        if 'CORE_COOKIES' not in self:
            c = SimpleCookie(self.get('HTTP_COOKIE', ''))

            cd = {}

            # TODO Fix for GAE
            for key in c.keys():
                cd[key] = c.get(key).value

            self['CORE_COOKIES'] = Hashmap(cd)

        return self['CORE_COOKIES']

    @property
    def BODY(self):
        if 'CORE_BODY' not in self:
            try:
                content_length = int(self.get('CONTENT_LENGTH', 0))
                stream = self.get('wsgi.input', None)
            except:
                return ''

            if stream is None or content_length is 0:
                return ''

            from cStringIO import StringIO

            body = StringIO(stream.read(content_length))

            self['CORE_BODY'] = body

        self['CORE_BODY'].seek(0)

        return self['CORE_BODY']

    @property
    def BODY2(self):
        if 'CORE_BODY' not in self:
            try:
                content_length = int(self.get('CONTENT_LENGTH', 0))
                stream = self.get('wsgi.input', None)
            except:
                return ''

            if stream is None or content_length is 0:
                return ''

            from cStringIO import StringIO

            body = StringIO(stream.read(content_length))

            self['CORE_BODY'] = body.read()

            from StringIO import StringIO as BytesIO

            maxread = max(0, content_length)

            stream = self.get('wsgi.input', None)
            body = BytesIO()
            while maxread > 0:
                part = stream.read(min(maxread, 1024))
                if not part: break
                body.write(part)
                maxread -= len(part)
            self['wsgi.input'] = body
            body.seek(0)

            #            print body.read()
            safe_env = {'QUERY_STRING': ''} # Build a safe environment for cgi
            for key in ('REQUEST_METHOD', 'CONTENT_TYPE', 'CONTENT_LENGTH'):
                if key in self: safe_env[key] = self[key]

            print safe_env

            import cgi

            data = cgi.FieldStorage(fp=body, environ=safe_env, keep_blank_values=True)
            print data.list[0].value

        return ''

    arguments = {}
    files = {}

    @property
    def FILE(self):
        files = {}
        for name, item in self.POST.items():
            if hasattr(item, 'filename'):
                files[name] = item

        return files

class Response(dict):
    code = 200
    COOKIES = Hashmap

    def __init__(self):
        self.update({
            'Powered-By': 'ExCore/1.0.1',
            'Content-Type': 'text/html'
        })
        self.COOKIES = Hashmap()

    type = property(
        lambda self: self.get("Content-Type"),
        lambda self, value: self.update({"Content-Type": value.strip()}),
        lambda self: self.__del__("Content-Type"),
        "Contect-Type"
    )

class Route(object):
    routes = {
        None: {
            None: {}
        }
    }

    def find(self, request):
        path = app.request.path
        method = app.request.method
        host = app.request.host
        subdomain = app.request.host.split(".", 2)[0]

        for skey in sorted(app.route.routes, reverse=True):
            if skey is None or host.startswith(skey):
                for mkey in sorted(app.route.routes[skey], reverse=True):
                    if mkey == method or mkey is None:
                        for rkey in sorted(app.route.routes[skey][mkey]):
                            result = rkey.match(path)

                            if result:
                                return app.route.routes[skey][mkey][rkey], result.groups()

                                #        # TODO make this easy
                                #        sd = app.route.routes.get('*', app.route.routes[None])
                                #        md = sd.get(method, sd[None])
                                #
                                #        for val in md:
                                #            result = val.match(path)
                                #
                                #            if result:
                                #                return md[val], result.groups()

        return None, None

    def prefix(self, px=None):
        if px is not None:
            self.__dict__['app_prefix'] = px
        else:
            return self.__dict__.get('app_prefix')

    def subdomain(self, sd=None):
        if sd is not None:
            self.__dict__['app_subdomain'] = sd
        else:
            return self.__dict__.get('app_subdomain')

    def redirect(self, to, args={}):
        if hasattr(to, 'route'):
            to = '/' + to.route

        app.response.code = 302
        app.response['Location'] = str(to)

        return ""

    def __call__(self, rule=None, methods=None, subdomain=None, handler=None):
        def wrapper(func):
            route = rule.strip('/') if rule is not None else func.__name__
            prefix = self.__dict__.get('app_prefix', None)
            sub_domain = subdomain if subdomain is not None else self.__dict__.get('app_subdomain', None)

            if prefix is not None:
                route = prefix.strip('/') + '/' + route

            regexp = re.compile('^/' + route + '/?$')

            if sub_domain not in app.route.routes:
                app.route.routes[sub_domain] = {}

            for method in methods if isinstance(methods, list) else [methods]:
                # If method doesnt exist then add it
                if method not in app.route.routes[sub_domain]:
                    app.route.routes[sub_domain][method] = {}

                app.route.routes[sub_domain][method][regexp] = func

            func.__dict__['route'] = route

            # Return original function for future reuse
            return func

        if handler is not None:
            wrapper(handler)

        return wrapper

    def __repr__(self):
        var = ''

        for sd, mds in sorted(app.route.routes.items()):
            var += '\t' + str(sd) + '\t+\n'
            for md, rs in mds.items():
                var += '\t\t' + str(md) + '\t+\n'
                for r, h in rs.items():
                    var += '\t\t\t' + str(r.pattern) + ' -> ' + h.__name__ + '\n'

        return "<pre>\r\n%s\r\n</pre>" % var

class Config(Hashmap):
    def __init__(self, list={}, **kwds):
        # TODO set super calling

        self.VIEWS_DIR = "views"

    def __call__(self, res):
        from types import ModuleType

        if type(res) is dict: # Populate from dictionary
            self.update(res)
        elif type(res) is str: # Load frim string

            if hasattr(self, '__metaclass__') and isinstance(self.__metaclass__, app):
                res = os.path.join(self.__metaclass__.path, res)

            if res.endswith('.py'):
                execfile(res, {}, self)
            elif res.endswith('.json'):
                self.update(json.loads(open(res, 'r').read()))
            elif res.endswith('.xml'):
                self.update(xml2array(file_name=res))
            elif res.endswith('.ini'):
                from ConfigParser import ConfigParser

                config = ConfigParser()
                config.read(res)
                result = Hashmap()

                for section in config.sections():
                    if section not in result:
                        result[section] = Hashmap()
                    for option in config.options(section):
                        value = config.get(section, option, False, None)
                        result[section][option] = value

                self.update(result)
            else:
                log.error("Unknown config format")

        elif type(res) is ModuleType: # TODO dirty hack, fix this
            res = os.path.abspath(res.__file__.replace('.pyc', '.py'))

            execfile(res, {}, self)
        else:
            log.error('ERROR: Provided config type not supported')
            exit()

        if 'APPS' in self and isinstance(self['APPS'], list):
            for a in self['APPS']:
                app(a)

        return self

    def extract(self):
        sys._getframe(1).f_globals.update(app.config)

class Session(Hashmap):
    @property
    def id(self):
        if 'SID' in app.cookies:
            sid = app.cookies['SID']
        else:
            import hashlib, time

            salt = str(time.time()) + os.getcwd()
            sid = hashlib.md5(salt).hexdigest().upper()
            app.request.COOKIES['SID'] = sid
            root_host = "." + ".".join(app.request.host.split(".")[-2:])
            month = 30 * 24 * 60 * 60
            app.cookies('SID', sid, expires=month, path='/', domain=root_host)

        return sid

    def set(self, key, val):
        sid = self.id
        session = os.environ.get(sid, "{}")
        session = json.loads(session)

        session[key] = val
        os.environ[sid] = json.dumps(session)

    def get(self, key, default=None):
        sid = self.id
        session = os.environ.get(sid, "{}")
        session = json.loads(session)

        return session.get(key, default)

    def exist(self):
        sid = self.id
        return sid in os.environ

    def register(self, name=None, handler=None):
        def wrapper(func):
            n = name if name is not None else func.__name__
            v = handler if handler is not None else func

            setattr(self, n, v)

        return wrapper

    def delete(self):
        sid = self.id

        app.cookies('SID', '', path='/')
        os.environ.__delitem__(sid)

    def __getattr__(self, key):
        return self.get(key)

    #    def __setattr__(self, key, val):
    #        return self.set(key, val)

    def __delattr__(self, key):
        return self.delete(key)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, val):
        return self.set(key, val)

    def __delitem__(self, key):
        return self.delete(key)

    def __repr__(self):
        return str(self.get(None))

class Log(object):
    def debug(self, str):
        print(str)

    def error(self, str):
        print(str)
        exit()

    def register(self, name=None, handler=None):
        def wrapper(func):
            n = name if name is not None else func.__name__
            v = handler if handler is not None else func

            setattr(self, n, v)

        return wrapper

class View(object):
    env = None

    def render(self, view, args={}):
        if hasattr(self, '__metaclass__') and isinstance(self.__metaclass__, app):
            view = os.path.join(self.__metaclass__.path, self.__metaclass__.config.VIEWS_DIR, view)

        return open(view, 'r').read()

    def notfound(self):
        def wrapper(fn):
            view.error_404 = fn

        return wrapper

    def error_404(self):
        return SYSTEM_PAGE_TEMPLATE % {
            'title': 'Page Not Found :(',
            'h1': '404',
            'h2': 'OOPS!',
            'message': 'Sorry, but the page you were trying to view does not exist.'
        }

    def error_500(self, message, trace):
        return SYSTEM_PAGE_TEMPLATE % {
            'title': 'Error / ' + str(message),
            'h1': '500',
            'h2': 'OOPS!',
            'message': trace if app.config.DEBUG else 'N/A'
        }

    def compress(self, content):
        import cStringIO
        from gzip import GzipFile

        buffer = cStringIO.StringIO()
        gz_file = GzipFile(None, 'wb', 9, buffer)
        gz_file.write(content)
        gz_file.close()
        return buffer.getvalue()

    def media(self, app_name=None, file_path=None):
        if app_name is None or file_path is None:
            app.response.code = 404
            return str(view.error_404())

        if app_name in app.apps:
            a = app.apps[app_name]
            file_path = os.path.join(a.path, 'media', file_path)

            # TODO Fix for GAE
            #            try:
            try:
                file = open(file_path, 'rb')
            #            except IOError as e:
            #                return str(e.args) + e.filename
            except IOError as e:
                app.response.code = 404
                print str(e.args) + e.filename
                return ''

            import mimetypes

            file_type = mimetypes.guess_type(app.request.path)

            if file_type[0] is not None:
                app.response.type = file_type[0]
            else:
                app.response.type = "application/octet-stream"

            return file

    def register(self, name=None, handler=None):
        def wrapper(func):
            n = name if name is not None else func.__name__
            v = handler if handler is not None else func

            setattr(self, n, v)

        return wrapper

    def __call__(self, view=None, handler=None):
        def wrapper(func):
            view_name = view if view else func.__name__ + '.html'

            if hasattr(self, '__metaclass__') and isinstance(self.__metaclass__, app):
                func.__dict__['view'] = os.path.join(self.__metaclass__.path, self.__metaclass__.config.VIEWS_DIR, view_name)
            else:
                func.__dict__['view'] = view_name

            return func

        if handler is not None:
            wrapper(handler)

        return wrapper

class Model(object):
    engine = 'mysql'

class Cookies(Hashmap):
    def __call__(self, key, val, expires=None, path='/', domain=None):
        params = []

        params.append("%s=%s" % (key, val))

        if expires:
            import datetime

            delta = datetime.datetime.now() + datetime.timedelta(seconds=expires)
            params.append("expires=%s" % delta.strftime("%a, %d-%b-%Y %H:%M:%S PST"))

        if path:
            params.append("path=%s" % path)

        if domain:
            params.append("domain=%s" % domain)

        app.response['Set-Cookie'] = ';'.join(params)

        return app.response['Set-Cookie']

    def __get__(self, item, cls):
        if len(self) == 0:
            c = SimpleCookie(app.request.get('HTTP_COOKIE', ''))

            # TODO Fix for GAE
            for key in c.keys():
                self[key] = c.get(key).value

        return self

class app(object):
    apps = Hashmap()
    config = Config()
    view = View()
    request = Request()
    response = Response()
    log = Log()
    route = Route()
    session = Session()
    get = request.GET
    post = request.POST
    cookies = Cookies()

    name = None
    path = None

    def __init__(self, n):
        super(app, self).__init__()

    # Realize singleton class pattern
    def __new__(cls, name):
        app_name = name.split('.')[-1]

        if app_name not in cls.apps:
            a = super(app, cls).__new__(cls)

            cls.apps[app_name] = a

            module = __import__(name) if name not in sys.modules else sys.modules[name]
            app_path = os.path.abspath(os.path.dirname(module.__file__))

            a.name = app_name
            a.path = app_path
            a.config = Config()
            a.config.update(cls.config)
            a.config.__metaclass__ = a
            a.view = View()
            a.view.__metaclass__ = a
            a.route = Route()
            a.route(rule='/(' + app_name + ')/media/(.*)', handler=a.view.media, subdomain=None)

        return cls.apps[app_name]

    def register(self, name=None):
        def wrapper(func):
            setattr(self, name if name else func.__name__, func)

            return func

        return wrapper

    def render(self, view, args={}):
        vars = {
            'app': app
        }

        if args:
            vars.update(args)

        view = os.path.join(self.path, self.config.VIEWS_DIR, view)

        content = app.view.render(view, vars)

        if isinstance(content, unicode):
            content = content.encode('utf-8')
        else:
            content = str(content)

        return content

    def file(self, path, type=None):
        # TODO Fix for GAE
        try:
            file = open(path, 'rb')
        except IOError as e:
            app.response.code = 404
            return str(e.args) + e.filename

        if type is None:
            import mimetypes

            file_type = mimetypes.guess_type(path)

            if file_type[0] is not None:
                app.response.type = file_type[0]
            else:
                app.response.type = "application/octet-stream"
        else:
            app.response.type = type

        return file

    def __call__(self, name):
        return self.__new__(app, name)

    def __repr__(self):
        return "[%s]" % self.name

    # TODO Fix for GAE
    #    @staticmethod

    class WSGI(object):
        def __call__(self, environ, start_response):
            content = ''
            response_headers = []
            app.cookies = Cookies()
            app.request = Request()
            app.response = Response()
            app.response.type = "text/html"

            try:
                app.request.bind(environ)

                # Get content
                handler, args = route.find(app.request)

                if handler is not None:
                    content = handler(*args)
                else:
                    app.response.code = 404
                    handler = view.error_404
                    content = handler()

                if hasattr(content, 'read'): # Binary file, do not process it via template engine
                    if 'wsgi.file_wrapper' in environ:
                        content = environ['wsgi.file_wrapper'](content, 4096) # Block size
                    else:
                        content = str(content.read())
                else:
                    if 'view' in handler.__dict__ and (isinstance(content, dict) or content is None):
                        vars = {
                            'app': app
                        }

                        if isinstance(content, dict):
                            vars.update(content)

                        content = app.view.render(handler.__dict__['view'], vars)

                        if isinstance(content, unicode):
                            content = content.encode('utf-8')
                        else:
                            content = str(content)
                    else:
                        if isinstance(content, tuple):
                            if len(content) == 2:
                                app.response.code = content[1]

                            if len(content) == 3:
                                app.response.type = content[2]

                            content = content[0]
                        elif isinstance(content, (list, dict)): # Looks like we need to return JSON object
                            app.response.type = 'application/json'
                            content = json.dumps(content)
                        else:
                            content = str(content)

                            #                    if app.response.type in CONTENT_TO_COMPRESS and app.request.headers.get('HTTP_ACCEPT_ENCODING', '').find('gzip') > -1:
                            #                        app.response.headers['Content-Encoding'] = 'gzip'
                            #                        app.response.headers['Vary'] = 'Accept-Encoding'
                            #
                            #                        content = app.view.compress(content)

                response_headers = list(app.response.items())
                #                map(lambda x: response_headers.append(('Set-Cookie', '='.join(x))), app.response.COOKIES)

            except (KeyboardInterrupt, SystemExit, MemoryError):
                raise
            except (Exception):
                import traceback

                error_type, error_value, trace = sys.exc_info()
                trace_list = traceback.format_tb(trace, None)

                app.response.code = 500
                content = view.error_500(error_value.message, '\n'.join(trace_list))

            start_response('%s %s' % (app.response.code, HTTP_STATUS_CODES.get(app.response.code, 'N/A')), response_headers)

            if PY3:
                return [str.encode(content)]
            else:
                return content

    @classmethod
    def run(cls, host='0.0.0.0', port='8080'):
        from wsgiref.simple_server import make_server

        exit_code = 0

        def start_server():
            httpd = make_server(host, int(port), cls.WSGI())
            httpd.serve_forever()

        # Auto reload server on file change. Only in DEBUG mode
        def auto_reload():
            _files = {}

            while True:
                for module in sys.modules.values():
                    if not hasattr(module, '__file__'):
                        continue

                    path = getattr(module, '__file__')

                    if not path:
                        continue

                    if os.path.splitext(path)[1] in ['.pyc', '.pyo', '.pyd']:
                        path = path[:-1]

                    if path in _files:
                        if not os.path.isfile(path) or _files[path] != os.stat(path).st_mtime:
                            sys.stdout.write('[%s] module is changed. Reloading...' % module.__name__)

                            sys.exit(10)
                    else:
                        if os.path.isfile(path):
                            _files[path] = os.stat(path).st_mtime

                time.sleep(1)

        try:
            if app.config.DEBUG:
                import threading, subprocess

                if not os.environ.get('IS_STARTED', None):
                    os.environ['IS_STARTED'] = 'true'

                    server_string = '------- Serving on port %s -------' % port
                    cls.log.debug('-' * len(server_string))
                    cls.log.debug(server_string)
                    cls.log.debug('-' * len(server_string))

                    exit_code = 10

                    while exit_code is 10:
                        exit_code = subprocess.call([sys.executable] + sys.argv, env=os.environ)
                        print(' done')
                else:
                    try:
                        thread = threading.Thread(target=start_server)
                        thread.setDaemon(True)
                        thread.start()

                        auto_reload()
                    except KeyboardInterrupt:
                        pass
            else:
                server_string = '------- Serving on port %s -------' % port
                cls.log.debug('-' * len(server_string))
                cls.log.debug(server_string)
                cls.log.debug('-' * len(server_string))

                start_server()

        except KeyboardInterrupt:
            print ("Bye")

        exit(exit_code)

request = app.request
response = app.response
config = app.config
log = app.log
route = app.route
view = app.view
session = app.session