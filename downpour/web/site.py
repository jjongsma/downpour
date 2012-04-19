from downpour.web import account, browse, downloads, feeds, libraries, remote, search
from downpour.web import settings, status, share, users, work, common, shares
from twisted.web import static, server

class SiteRoot(common.Resource):

    def __init__(self, mediadir, app):
        common.Resource.__init__(self)
        self.putChild('', self)
        self.putChild('resume', Resume())
        self.putChild('pause', Pause())
        self.putChild('account', account.Root())
        self.putChild('browse', browse.Root())
        self.putChild('downloads', downloads.Root())
        self.putChild('feeds', feeds.Root())
        self.putChild('libraries', libraries.Root())
        self.putChild('media', static.File(mediadir))
        self.putChild('remote', remote.Root())
        self.putChild('search', search.Root())
        self.putChild('settings', settings.Root())
        self.putChild('status', status.Root())
        self.putChild('share', share.Root())
        self.putChild('shares', shares.Root())
        self.putChild('users', users.Root())
        self.putChild('work', work.Root())
    
    def render_GET(self, request):
        if self.is_logged_in(request):
            request.redirect('/downloads/')
        else:
            request.redirect('/status/')
        request.finish()
        return server.NOT_DONE_YET

class Pause(common.AuthenticatedResource):

    def render_GET(self, request):
        def finish(result):
            request.redirect('/')
            request.finish()
        request.application.pause().addCallback(finish)
        return server.NOT_DONE_YET

class Resume(common.AuthenticatedResource):

    def render_GET(self, request):
        def finish(result):
            request.redirect('/')
            request.finish()
        request.application.resume().addCallback(finish)
        return server.NOT_DONE_YET
