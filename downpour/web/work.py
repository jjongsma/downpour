from downpour.web import common, auth
from twisted.web import static, server
import os, shutil

class Root(common.AuthenticatedResource):

    def __init__(self, *args, **kwargs):
        common.AuthenticatedResource.__init__(self, *args, **kwargs)

    def getChild(self, path, request):
        if not self.is_logged_in(request):
            return self
        manager = self.get_manager(request)
        filepath = manager.get_work_directory()
        return File(str(filepath)).getChild(path, request)

    def render_GET(self, request):
        if 'd' in request.args:
            path = request.args['d'][0]
            if path[len(path)-1] == '/':
                path = path[:len(path)-1]
            redirect = os.path.dirname(path)

            manager = self.get_manager(request)
            path = '%s%s' % (manager.get_work_directory(), path)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

            request.redirect('work%s' % redirect)
            request.finish()
            return server.NOT_DONE_YET
        else:
            return 'No action specified'

class File(static.File):

    def __init__(self, *args, **kwargs):
        static.File.__init__(self, *args, **kwargs)

    def directoryListing(self):
        lister = DirectoryIndex(self.path,
            self.listNames(),
            self.contentTypes,
            self.contentEncodings,
            self.defaultType)
        return lister

class DirectoryIndex(static.DirectoryLister, common.Resource):

    def __init__(self, *args, **kwargs):
        static.DirectoryLister.__init__(self, *args, **kwargs)

    def render(self, request):
        if self.dirs is None:
            directory = os.listdir(self.path)
            directory.sort()
        else:
            directory = self.dirs

        manager = self.get_manager(request)
        relPath = self.path[len(manager.get_work_directory()):]
        dirs, files = self._getFilesAndDirectories(directory)
        context = {
            'title': 'Files: %s/' % relPath,
            'path': relPath,
            'directories': dirs,
            'files': files
            }

        return self.render_template('work/directory.html', request, context)
