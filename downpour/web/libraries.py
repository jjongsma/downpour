from downpour.web import common
from downpour.core import models, organizer
from twisted.web import server

class Root(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self);
        self.putChild('save', Save())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            return Detail(int(path))

    def render_GET(self, request):
        manager = self.get_manager(request)
        userlibs = manager.get_libraries()
        userdir = manager.get_library_directory()
        context = {
            'title': 'Media Locations',
            'basedir': userdir,
            'mediatypes': organizer.get_media_types(),
            'patterns': organizer.get_file_patterns(),
            'libraries': organizer.get_media_libraries(userlibs)
        }
        return self.render_template('libraries/index.html', request, context)

class Save(common.AuthenticatedResource):

    def __init__(self, library=None):
        common.AuthenticatedResource.__init__(self)
        self.library = library

    def render_POST(self, request):
        manager = self.get_manager(request)
        mediatype = request.args['media_type']
        directory = request.args['directory']
        keepall = request.args['keep']
        pattern = request.args['pattern']

        libraries = organizer.get_media_libraries(manager.get_libraries())
        for i in range(0, len(mediatype)):
            if not libraries[mediatype[i]]:
                l = models.Library()
                l.user = self.get_user(request)
                l.media_type = unicode(mediatype[i])
                manager.store.add(l)
                libraries[mediatype[i]] = l
            libraries[mediatype[i]].directory = unicode(directory[i])
            libraries[mediatype[i]].pattern = unicode(pattern[i])
            libraries[mediatype[i]].keepall = (keepall[i] == '1')
        manager.store.commit()
        request.redirect('/')
        request.finish()
        return server.NOT_DONE_YET
