import pkg_resources
from twisted.web import static, server
from downpour2.web import common

class SiteRoot(common.Resource):

    def __init__(self, app):

        common.Resource.__init__(self)

        self.putChild('', self)
        self.putChild('media', MediaPath(
            pkg_resources.resource_filename("downpour2.web", "/media")))
    
    def render_GET(self, request):

        # TODO populate overview/status info depending on login state
        return self.render_template('index.html', request, {
                'title': 'Downpour'
            });

class MediaPath(static.File):

    def directoryListing(self):
        return self.childNotFound
