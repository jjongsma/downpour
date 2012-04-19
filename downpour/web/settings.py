from downpour.web import common
from downpour.core import models
from twisted.web import server

class Root(common.AdminResource):

    def __init__(self):
        common.AdminResource.__init__(self)
        self.putChild('', self);
        self.putChild('save', Save())

    def render_GET(self, request):
        manager = self.get_manager(request)
        settings = manager.store.find(models.Setting)
        setdict = {}
        if settings.count():
            setdict = dict(zip([s.name for s in settings], [s.value for s in settings]))
        context = {
            'title': 'Settings',
            'settings': setdict
        }
        return self.render_template('settings/index.html', request, context)

class Save(common.AdminResource):

    def render_POST(self, request):
        for s in request.args:
            request.application.set_setting(unicode(s), unicode(request.args[s][0]))

        # Force bandwidth filters to reload
        manager = self.get_manager(request)
        manager.get_upload_rate_filter()
        manager.get_download_rate_filter()

        request.redirect('/')
        request.finish()
        return server.NOT_DONE_YET
