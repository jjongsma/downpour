import libtorrent as lt
from twisted.web import server
from downpour2.core import store
from downpour2.core.transfers import state, event
from downpour2.core.util import StormModelEncoder
from downpour2.web import common, demo


class Root(common.RoutedResource):
    def __init__(self, application, environment):
        super(Root, self).__init__(application, environment)
        self.putChild('', self)
        self.putChild('add', Add(application, environment))
        self.putChild('status', Status(application, environment))
        self.putChild('detail', Detail(application, environment))


class Detail(common.Resource):
    def __init__(self, application, environment):
        super(Detail, self).__init__(application, environment)

    def getChild(self, path, request):
        if path.isdigit():
            return Transfer(path, self.application, self.environment)
        return common.NotFoundResource(self.application, self.environment)


class Transfer(common.AuthenticatedResource):
    def __init__(self, id, application, environment):
        super(Transfer, self).__init__(application, environment)
        self.id = id

    def render_GET(self, request):
        agent = self.application.transfer_manager.user(self.get_user(request).id)
        transfer = agent.client(self.id)
        if transfer is not None:
            return self.render_json(transfer)
        return self.render_json_error(request, 404, 'Transfer not found')


class Status(common.Resource):
    def __init__(self, application, environment):
        super(Status, self).__init__(application, environment)
        self.putChild('', self)
        self.putChild('demo', demo.DemoStatus(application, environment))

    def render_GET(self, request):
        user = self.get_user(request)
        if user is None:
            return self.render_json([])
        else:
            clients = self.application.transfer_manager.user(self.get_user(request).id).clients
            return self.render_json(
                [self.format_transfer(c) for c in clients]
            )

    def format_transfer(self, client):
        encoder = StormModelEncoder()
        t = encoder.default(client.transfer)
        t['state'] = state.describe(t['state'])
        t['state'].start = client.can(event.START)
        t['state'].stop = client.can(event.STOP)
        t['state'].remove = client.can(event.REMOVE)

        for f in ('health',
                  'uploadrate',
                  'downloadrate',
                  'connections',
                  'connection_limit',
                  'elapsed',
                  'timeleft'):
            t[f] = getattr(client.transfer, f)

        return t


class Add(common.AuthenticatedResource):
    def __init__(self, application, environment):
        super(Add, self).__init__(application, environment)
        self.putChild('', self)
        self.putChild('url', AddURL(application, environment))
        self.putChild('torrent', AddTorrent(application, environment))

    def render_GET(self, request):
        return self.render_json_error(request, 405, 'Not implemented')


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
            request.redirect('/transfers/status')
            request.finish()
            return server.NOT_DONE_YET
        else:
            return self.render_json_error(request, 400, 'No valid torrent was found')


class AddURL(common.AuthenticatedResource):
    def __init__(self, application, environment):
        super(AddURL, self).__init__(application, environment)
        self.putChild('', self)

    def render(self, request):
        if 'url' in request.args and len(request.args['url'][0]) > 0:
            t = store.Transfer()
            t.user = self.get_user(request)
            t.state = state.QUEUED
            t.url = unicode(request.args['url'][0])
            self.application.store.commit()
            self.application.transfer_manager.add(t)
            request.redirect('/transfers/status')
            request.finish()
            return server.NOT_DONE_YET
        else:
            return self.render_json_error(request, 400, 'URL was not specified')


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
