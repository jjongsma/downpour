from downpour.web import common
from downpour.core import models
from storm import expr
from twisted.web import server, client
from twisted.python.failure import Failure
import json, urllib

class Root(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self);
        self.putChild('add', Add())
        self.putChild('save', Save())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            return Detail(int(path))

    def render_GET(self, request):
        manager = self.get_manager(request)
        user = self.get_user(request)
        shares = manager.store.find(models.RemoteShare,
            models.RemoteShare.user == user
            ).order_by(expr.Asc(models.RemoteShare.name))
        context = {
            'title': 'Remote Shares',
            'shares': shares
        }
        return self.render_template('shares/index.html', request, context)

class Add(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)

    def render_GET(self, request):
        manager = self.get_manager(request)
        context = {
            'title': 'Add Remote Share',
            'share': { }
        }
        return self.render_template('shares/form.html', request, context)

class Detail(common.AuthenticatedResource):

    def __init__(self, id):
        common.AuthenticatedResource.__init__(self)
        self.id = id

    def getChild(self, path, request):
        if (path == ''):
            return self
        manager = self.get_manager(request)
        if manager:
            share = manager.store.find(models.RemoteShare, models.RemoteShare.id == self.id)[0]
            if (path == 'edit'):
                return Edit(share)
            elif (path == 'save'):
                return Save(share)
            elif (path == 'delete'):
                return Delete(share)
            elif (path == 'browse'):
                return Browse(share)
        else:
            return self

    def render_GET(self, request):
        manager = self.get_manager(request)
        share = manager.store.find(models.RemoteShare, models.RemoteShare.id == self.id)[0]
        context = {'title': share.name,
                   'share': share
                   }
        return self.render_template('shares/detail.html', request, context)

class Edit(common.AuthenticatedResource):

    def __init__(self, share):
        common.AuthenticatedResource.__init__(self)
        self.share = share

    def render_GET(self, request):
        manager = self.get_manager(request)
        context = {
            'title': 'Edit Remote Share',
            'share': self.share
        }
        return self.render_template('shares/form.html', request, context)

class Save(common.AuthenticatedResource):

    def __init__(self, share=None):
        common.AuthenticatedResource.__init__(self)
        self.share = share

    def render_POST(self, request):
        manager = self.get_manager(request)
        converters = {
            'name': lambda v: unicode(v),
            'address': lambda v: unicode(v),
            'username': lambda v: unicode(v),
            'password': lambda v: unicode(v)
        }

        # Use specified model or create new for adding
        share = self.share
        if not share:
            share = models.RemoteShare()
            share.user = self.get_user(request)
            manager.store.add(share)

        # Updated object from form
        for k in request.args:
            v = request.args[k][0]
            if hasattr(share, k) and k in converters:
                setattr(share, k, converters[k](request.args[k][0]))
        manager.store.commit()

        request.redirect('/shares')
        request.finish()
        return server.NOT_DONE_YET

class Delete(common.AuthenticatedResource):

    def __init__(self, share):
        common.AuthenticatedResource.__init__(self)
        self.share = share

    def render_GET(self, request):
        manager = self.get_manager(request)
        manager.store.remove(self.share)
        manager.store.commit()
        request.redirect('/shares')
        request.finish()
        return server.NOT_DONE_YET

class Browse(common.AuthenticatedResource):

    def __init__(self, share, path = '', parent = None):
        common.AuthenticatedResource.__init__(self)
        self.share = share
        if path != '':
            path = path + '/'
        self.path = path
        self.parent = parent

    def render_GET(self, request):
        self.show_listing(request)
        return server.NOT_DONE_YET

    def getChild(self, path, request):
        if (path == ''):
            return self
        else:
            parent = self.path
            if self.parent:
                parent = self.parent + parent
            return Browse(self.share, path, parent)

    def show_listing(self, request):
        fullpath = self.path
        if self.parent:
            fullpath = self.parent + fullpath
        authParams = 'username=%s&password=%s' % (self.share.username, self.share.password)
        url = '%s/share/%s?%s' % (self.share.address, fullpath, authParams)
        downloadUrl = '%s/share/%s%%s?%s' % (self.share.address,
            fullpath.replace('%', '%%'), authParams)
        response = client.getPage(str(url))
        response.addCallback(self.listing_success, downloadUrl, fullpath, request)
        response.addErrback(self.listing_failed, request)

    def listing_success(self, unparsed, downloadUrl, fullpath, request):
        manager = self.get_manager(request)
        listing = self.parse_listing(unparsed)
        context = {
            'title': '%s: /%s' % (self.share.name, urllib.unquote(fullpath)),
            'downloadUrl': downloadUrl,
            'path': self.path,
            'directories': listing[0],
            'files': listing[1],
            'share': self.share
        }
        request.write(
            self.render_template('shares/browse.html', request, context))
        request.finish()

    def listing_failed(self, failure, request):
        failure.printTraceback()
        request.write(
            self.render_template('errors/error.html', request, {
                'title': 'Could not retrieve directory listing',
                'message': failure.getErrorMessage()
                })
            )
        request.finish()

    def parse_listing(self, unparsed):

        directories = []
        files = []

        parsed = json.loads(unparsed)
        for i in parsed:
            if i['type'] == 'directory':
                directories.append(i)
            else:
                files.append(i)

        return [directories, files]
