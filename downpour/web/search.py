from downpour.web import common

class Root(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)

    def render_GET(self, request):
        context = {'title': 'Search'}
        return self.render_template('search/index.html', request, context)

    def render_POST(self, request):
        context = {'title': 'Search'}
        return self.render_template('search/search.html', request, context)
