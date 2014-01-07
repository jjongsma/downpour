import pkg_resources
from twisted.web import static
from downpour2.web import common, account, transfers


class SiteRoot(common.Resource):

    def __init__(self, application, environment):

        super(SiteRoot, self).__init__(application, environment)

        self.putChild('', self)
        self.putChild('media', MediaPath(pkg_resources.resource_filename("downpour2.web", "/media")))
        self.putChild('account', account.Root(application, environment))
        self.putChild('transfers', transfers.Root(application, environment))

    def add_child(self, path, resource):
        if path in self.children:
            raise ValueError('Module path "%s" is already registered' % path)
        self.putChild(path, resource)

    def render_GET(self, request):

        if self.get_user(request) is not None:
            return self.render_template('core/index.html', request, {
                'title': 'Downpour'
            })
        else:
            return self.render_template('core/status.html', request, {
                'title': 'Downpour'
            })


class MediaPath(static.File):

    def directoryListing(self):
        return self.childNotFound
