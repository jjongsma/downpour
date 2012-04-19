from downpour.web import common
from downpour.core import models
from twisted.web import server

class Root(common.AdminResource):

    def __init__(self):
        common.AdminResource.__init__(self)
        self.putChild('', self);
        self.putChild('add', Add())
        self.putChild('save', Save())

    def getChild(self, path, request):
        if path in self.children:
            return self.children[path]
        elif path.isdigit():
            return Detail(int(path))

    def render_GET(self, request):
        manager = request.application.get_manager()
        context = {
            'title': 'Users',
            'userdir': manager.get_user_directory(),
            'users': manager.store.find(models.User).order_by(models.User.username)
        }
        return self.render_template('users/index.html', request, context)

class Add(common.AdminResource):

    def __init__(self):
        common.AdminResource.__init__(self)
        self.putChild('', self)

    def render_GET(self, request):
        manager = request.application.get_manager()
        context = {
            'title': 'Add User',
            'edituser': {},
            'userdir': manager.get_user_directory()
        }
        return self.render_template('users/form.html', request, context)

class Detail(common.AdminResource):

    def __init__(self, id):
        common.AdminResource.__init__(self)
        self.id = id

    def getChild(self, path, request):
        if (path == ''):
            return self
        manager = request.application.get_manager()
        if manager:
            user = manager.store.find(models.User, models.User.id == self.id).one()
            if (path == 'edit'):
                return Edit(user)
            elif (path == 'save'):
                return Save(user)
            elif (path == 'delete'):
                return Delete(user)
        else:
            return self

    def render_GET(self, request):
        manager = request.application.get_manager()
        user = manager.store.find(models.User, models.User.id == self.id).one()
        context = {'title': user.username,
                   'edituser': user,
                   'userdir': manager.get_user_directory()
                   }
        return self.render_template('users/detail.html', request, context)

class Edit(common.AdminResource):

    def __init__(self, user):
        common.AdminResource.__init__(self)
        self.user = user

    def render_GET(self, request):
        manager = request.application.get_manager()
        context = {
            'title': 'Edit User',
            'edituser': self.user,
            'userdir': manager.get_user_directory()
        }
        return self.render_template('users/form.html', request, context)

class Save(common.AdminResource):

    def __init__(self, user=None):
        common.AdminResource.__init__(self)
        self.user = user

    def render_POST(self, request):
        manager = request.application.get_manager()
        converters = {
            'username': lambda v: unicode(v),
            'password': lambda v: unicode(v),
            'email': lambda v: unicode(v),
            'directory': lambda v: unicode(v),
            'max_downloads': lambda v: int(v),
            'max_rate': lambda v: int(v),
            'share_enabled': lambda v: bool(v),
            'share_password': lambda v: unicode(v),
            'share_max_rate': lambda v: int(v),
            'admin': lambda v: bool(v)
        }

        # Use specified model or create new for adding
        user = self.user
        if not user:
            user = models.User()
            user.user = self.get_user(request)
            manager.store.add(user)

        # Updated object from form
        for k in request.args:
            v = request.args[k][0]
            if k == 'password' and not v:
                continue
            if hasattr(user, k) and k in converters:
                setattr(user, k, converters[k](request.args[k][0]))
        # Boolean special handling from forms
        if not 'share_enabled' in request.args:
            user.share_enabled = False
        manager.store.commit()

        request.redirect('/users')
        request.finish()
        return server.NOT_DONE_YET

class Delete(common.AdminResource):

    def __init__(self, user):
        common.AdminResource.__init__(self)
        self.user = user

    def render_GET(self, request):
        manager = request.application.get_manager()
        manager.store.remove(self.user)
        request.redirect('/users')
        request.finish()
        return server.NOT_DONE_YET
