from downpour.web import common

class Root(common.Resource):

    def __init__(self):
        common.Resource.__init__(self)
        self.putChild('', self)

    def render_GET(self, request):
        return self.render_template('status/index.html', request, {
                'title': 'Server Status',
                'status': request.application.get_manager().get_status()
            })
