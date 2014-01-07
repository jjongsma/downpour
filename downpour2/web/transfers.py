from twisted.web import server
import libtorrent as lt
from downpour2.core import store
from downpour2.web import common


class Root(common.AuthenticatedResource):

    def __init__(self, application, environment):
        common.AuthenticatedResource.__init__(self, application, environment)
        self.putChild('', self)
        self.putChild('add', Add(application, environment))

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            # Transfer detail
            return common.NotFoundResource()

    def render_GET(self, request):
        context = {'title': 'Transfers'}
        request.setHeader('X-Request-Path', '/transfers/')
        return self.render_template('core/transfers/index.html', request, context)


class Add(common.AuthenticatedResource):

    def __init__(self, application, environment):
        super(Add, self).__init__(application, environment)
        self.putChild('', self)
        self.putChild('url', AddURL(application, environment))
        self.putChild('torrent', AddTorrent(application, environment))

    def render_GET(self, request):
        return 'Not implemented'


class AddTorrent(common.AuthenticatedResource):

    def __init__(self, application, environment):
        super(AddTorrent, self).__init__(application, environment)
        self.putChild('', self)

    def render_POST(self, request):
        if 'torrent' in request.args and len(request.args['torrent'][0]) > 0:
            t = store.Transfer()
            t.mime_type = u'application/x-bittorrent'
            t.metadata = request.args['torrent'][0]
            ti = lt.torrent_info(lt.bdecode(t.metadata))
            t.description = unicode(ti.name())
            t.size = int(ti.total_size())
            #self.get_manager(request).add_download(t)
            request.redirect('/transfers/')
            request.finish()
            return server.NOT_DONE_YET
        else:
            return self.render_template('core/errors/error.html', request, {
                'title': 'No Torrent Found',
                'message': 'Torrent was not uploaded'
            })


class AddURL(common.AuthenticatedResource):

    def __init__(self, application, environment):
        super(AddURL, self).__init__(application, environment)
        self.putChild('', self)

    def render(self, request):
        if 'url' in request.args and len(request.args['url'][0]) > 0:
            t = store.Transfer()
            t.url = unicode(request.args['url'][0])
            # self.get_manager(request).add_download(t)
            request.redirect('/transfers/')
            request.finish()
            return server.NOT_DONE_YET
        else:
            return self.render_template('core/errors/error.html', request, {
                'title': 'No URL Found',
                'message': 'URL was not specified'
            })


def numcmp(zero_null=False, reverse=False):
    def cmpfn(x, y):
        x = float(x)
        y = float(y)
        if x == y:
            return 0
        if x is None or (zero_null and x <= 0) or (not zero_null and x < 0):
            return 1
        if y is None or (zero_null and y <= 0) or (not zero_null and y < 0):
            return -1
        if reverse:
            return cmp(y, x)
        else:
            return cmp(x, y)
    return cmpfn
