from downpour.web import common
from downpour.core import models, organizer
from downpour import download
from twisted.web import server
from twisted.internet import defer
from storm import expr
import libtorrent as lt
import json, base64

class JSONRemoteResource(common.Resource):

    def render(self, request, *args):
        if not self.is_logged_in(request):
            request.setHeader('Status', '401 Not Authorized')
            request.write(json.dumps({ 'error': 'Not authorized' },
                indent=4))
            request.finish()
            return server.NOT_DONE_YET
        return common.Resource.render(self, request, *args)

    def get_user(self, request):
        user = common.Resource.get_user(self, request)
        if user is None:
            request.content.seek(0,0)
            params = json.loads(request.content.read())
            if '_username' in params:
                checkUser = request.application.get_store().find(models.User,
                    models.User.username == params['_username']).one()
                if checkUser.password == params['_password']:
                    self.set_user(checkUser, request)
                    user = checkUser
        return user

    def render_GET(self, request):

        request.setHeader('Status', '405 Method Not Allowed')
        request.write('GET not allowed')
        request.finish()

        return server.NOT_DONE_YET

    def render_POST(self, request):

        manager = self.get_manager(request)
        request.content.seek(0,0)
        postObj = json.loads(request.content.read())
        params = None
        if '_params' in postObj:
            params = postObj['_params']

        result = True
        try:
            result = self.call(manager, params)
        except Exception as e:
            result = { 'error': str(e) }
            request.setHeader('Status', '500 Server Error')

        request.write(json.dumps(result, indent=4))
        request.finish()
        return server.NOT_DONE_YET

    def call(self, manager, params=None):
        raise Exception('No command specified')

    def get_download_dict(self, manager, dl, show_files=False):

        client = manager.get_download_client(dl.id, True)

        feedid = None
        if dl.feed:
            feedid = dl.feed.id

        userid = None
        username = None
        if dl.user:
            userid = dl.user.id
            username = dl.user.username

        dldict = {
            'id': dl.id,
            'url': dl.url,
            'filename': dl.filename,
            'user': userid,
            'username': username,
            'feed': feedid,
            'media_type': dl.media_type,
            'mime_type': dl.mime_type,
            'health': dl.health,
            'description': dl.description,
            'size': dl.size,
            'active': dl.active,
            'status': download.Status.descriptions[dl.status],
            'status_code': dl.status,
            'status_message': dl.status_message,
            'size': dl.size,
            'progress': dl.progress,
            'downloaded': dl.downloaded,
            'downloadrate': int(dl.downloadrate),
            'uploaded': dl.uploaded,
            'uploadrate': int(dl.uploadrate),
            'added': dl.added,
            'started': dl.started,
            'completed': dl.completed,
            'deleted': dl.deleted,
            'importing': dl.importing,
            'imported': dl.imported,
            'elapsed': int(dl.elapsed),
            'timeleft': int(dl.timeleft),
            'running': (client.is_running() and True),
            'startable': (client.is_startable() and True),
            'stoppable': (client.is_stoppable() and True),
            'finished': (client.is_finished() and True)
        };

        if show_files:
            dldict['files'] = [f for f in client.get_files() if client]
        
        return dldict

class Root(JSONRemoteResource):

    def __init__(self):
        JSONRemoteResource.__init__(self)
        self.putChild('status', Status())
        self.putChild('downloads', Downloads())
        self.putChild('feeds', Feeds())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]

class Status(JSONRemoteResource):

    def call(self, manager, params=None):

        status = manager.get_status()

        result = {
            'status': status,
            'downloads': [self.get_download_dict(manager, dl)
                    for dl in manager.get_downloads()]
        }

        return result

class Downloads(JSONRemoteResource):

    def __init__(self):
        JSONRemoteResource.__init__(self)
        self.putChild('', self)
        self.putChild('add', AddDownload())
        self.putChild('addtorrent', AddTorrent())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            return Download(int(path))

    def call(self, manager, params=None):
        return [self.get_download_dict(manager, dl)
                for dl in manager.get_downloads()]

class Download(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id
        self.putChild('', self)
        self.putChild('start', StartDownload(id))
        self.putChild('stop', StopDownload(id))
        self.putChild('restart', RestartDownload(id))
        self.putChild('remove', RemoveDownload(id))
        self.putChild('update', UpdateDownload(id))

    def call(self, manager, params=None):
        return self.get_download_dict(manager, manager.get_download(self.id), True)

class AddDownload(JSONRemoteResource):

    def call(self, manager, params):

        if 'url' in params:
            dl = models.Download()
            dl.url = params['url']
            if 'media_type' in params:
                dl.media_type = params['media_type']
        else:
            raise Exception('URL not specified')

        manager.add_download(dl)
        return dl.id

class AddTorrent(JSONRemoteResource):

    def call(self, manager, params):

        if 'metadata' in params:
            dl = models.Download()
            dl.mime_type = u'application/x-bittorrent'
            dl.metadata = base64.decodestring(params['metadata'])
            dl.description = u'Imported torrent'
            if 'media_type' in params:
                dl.media_type = params['media_type']
        else:
            raise Exception('Torrent data not specified')

        manager.add_download(dl)
        return dl.id

class StopDownload(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id

    def call(self, manager, params):
        dfr = manager.stop_download(self.id)
        return True

class StartDownload(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id

    def call(self, manager, params):
        dfr = manager.start_download(self.id)
        return True

class RestartDownload(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id

    def call(self, manager, params):
        dfr = manager.stop_download(self.id)
        def finish(result):
            manager.start_download(self.id)
        dfr.addCallback(finish)
        dfr.addErrback(finish)
        return True

class RemoveDownload(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id

    def call(self, manager, params):
        dfr = manager.remove_download(self.id)
        return True

class UpdateDownload(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id

    def call(self, manager, params):
        dl = manager.get_download(self.id)
        if params['media_type']:
            dl.media_type = unicode(params['media_type'])
        # Reprocess library import if it is already imported
        if dl.imported:
            manager.process_download(dl, manager.get_download_client(dl.id))
        manager.store.commit()
        return True

class Feeds(JSONRemoteResource):

    def __init__(self):
        JSONRemoteResource.__init__(self)
        self.putChild('', self)
        self.putChild('add', AddFeed())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            return Feed(int(path))

    def call(self, manager, params=None):
        return [{
            'id': f.id,
            'user': f.user_id,
            'name': f.name,
            'url': f.url,
            'media_type': f.media_type,
            'modified': f.modified,
            'active': f.active,
            'auto_clean': f.auto_clean,
            'last_check': f.last_check,
            'last_update': f.last_update,
            'last_error': f.last_error,
            'update_frequency': f.update_frequency,
            'queue_size': f.queue_size,
            'save_priority': f.save_priority,
            'download_directory': f.download_directory,
            'rename_pattern': f.rename_pattern
            } for f in manager.get_feeds()]

class Feed(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id
        self.putChild('', self)
        self.putChild('remove', RemoveFeed(id))

    def call(self, manager, params=None):
        f = manager.get_feed(self.id)
        return {
            'id': f.id,
            'user': f.user_id,
            'name': f.name,
            'url': f.url,
            'media_type': f.media_type,
            'modified': f.modified,
            'active': f.active,
            'auto_clean': f.auto_clean,
            'last_check': f.last_check,
            'last_update': f.last_update,
            'last_error': f.last_error,
            'update_frequency': f.update_frequency,
            'queue_size': f.queue_size,
            'save_priority': f.save_priority,
            'download_directory': f.download_directory,
            'rename_pattern': f.rename_pattern
            }

class AddFeed(JSONRemoteResource):

    def call(self, manager, params):

        if 'url' in params and 'name' in params:
            f = models.Feed()
            f.url = params['url']
            f.name = params['name']
            if 'media_type' in params:
                f.media_type = params['media_type']
        else:
            raise Exception('URL not specified')

        manager.add_feed(f)
        return f.id

class RemoveFeed(JSONRemoteResource):

    def __init__(self, id):
        JSONRemoteResource.__init__(self)
        self.id = id

    def call(self, manager, params):
        dfr = manager.remove_feed(self.id)
        return True

