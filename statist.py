from core import app, config, view
import os, urllib, urllib2

app = app(__name__)

def statist(*args):
    files = []
    times = []
    ext = ''

    for base_path in args:
        base_path = base_path.strip('/')
        app_name = base_path[0:base_path.find('/')]
        app_id = app(app_name)

        file_path = os.path.join(app_id.path, base_path[base_path.find('/')+1:])
        files.append(file_path)
        times.append(str(int(os.path.getmtime(file_path))))

        ext = file_path.split('.')[-1]

    cache_base_name = '.'.join([str('-'.join(args).__hash__()), '.'.join(times), ext])
    cache_path_name = os.path.join(config.CACHE_PATH, cache_base_name)
    cache_web_name = '/'.join([config.CACHE_WEB_PATH, cache_base_name])

    if not os.path.exists(cache_path_name):
        soc = open(cache_path_name, 'wb')

        for file_path in files:
            file_data = open(file_path, 'rb').read()

            # Try to optimize content
            if ext == 'js' and not config.DEBUG:
                params = urllib.urlencode({
                    'js_code': file_data,
                    'compilation_level': 'WHITESPACE_ONLY',
                    'output_format': 'text',
                    'output_info': 'compiled_code'
                })

                file_data = urllib2.urlopen("http://closure-compiler.appspot.com/compile", params).read()

            if ext == 'css' and not config.DEBUG:
                params = urllib.urlencode({
                    'compresstext': file_data,
                    'type': 'CSS',
                    'redirect': 'on'
                })

                file_data = urllib2.urlopen("http://refresh-sf.com/yui/", params).read()

            soc.write(file_data)
            soc.write('\n')

        soc.close()

    return cache_web_name

view.env.globals.update(statist=statist)

@app.route('%s(.*)' % config.CACHE_WEB_PATH.strip('/'))
def cache_handler(file_name):
    file_path = os.path.join(config.CACHE_PATH, file_name.strip('/'))

    # TODO This affect to all calls headers
#    app.response.HEADERS.update({
#        'Cache-Control': 'public, max-age=315063001',
#        'Expires': 'Sat, 16 Oct 2021 23:34:42 GMT'
#    })

    return app.file(file_path)