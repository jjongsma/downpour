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

        if self.is_logged_in(request):
            request.redirect('/downloads/')
        else:
            request.redirect('/status/')
        request.finish()

        return server.NOT_DONE_YET

class MediaPath(static.File):

    def directoryListing(self):
        return self.childNotFound
