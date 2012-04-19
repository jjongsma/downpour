from twisted.web import resource, server, error
from downpour.core import VERSION, models
from storm import expr
import auth
import os, hashlib

def requestFactory(plugin):
    def factory(*args, **kwargs):
        return Request(plugin, *args, **kwargs)
    return factory

class Request(server.Request):

    def __init__(self, plugin, *args, **kwargs):
        server.Request.__init__(self, *args, **kwargs)
        self.application = plugin.application
        self.plugin = plugin
        self.templateFactory = plugin.templateFactory

def sessionFactory(plugin):
    def factory(*args, **kwargs):
        return Session(plugin, *args, **kwargs)
    return factory

class Session(server.Session):

    def __init__(self, plugin, *args, **kwargs):
        server.Session.__init__(self, *args, **kwargs)
        self.setAdapter(auth.IAccount, auth.Account)

class Resource(resource.Resource):

    templates = {}

    def getChild(self, *args):
        c = resource.Resource.getChild(self, *args)
        if c.__class__ == error.NoResource:
            return NotFoundResource()
        return c

    def is_logged_in(self, request):
        user = self.get_user(request)
        if user is not None:
            return True
        return False

    def require_authentication(self, request, path):
        if not self.is_logged_in(request):
            request.redirect(path)
            return False
        return True

    def get_user(self, request):
        account = request.getSession(auth.IAccount)
        if not account.user:
            userinfo = request.getCookie('DOWNPOUR_USER');
            if userinfo:
                (userid, userhash) = userinfo.split(':', 1)
                user = request.application.get_store().find(models.User,
                    models.User.id == int(userid)).one()
                comphash = hashlib.md5('%s:%s' % (user.username, user.password)).hexdigest();
                if userhash == comphash:
                    account.user = user
        return account.user

    def set_user(self, user, request):
        account = request.getSession(auth.IAccount)
        if user is not None:
            userhash = hashlib.md5('%s:%s' % (user.username, user.password)).hexdigest()
            request.addCookie('DOWNPOUR_USER', '%s:%s' % (user.id, userhash), path='/')
        else:
            request.addCookie('DOWNPOUR_USER', '', path='/', expires=-1)
        account.user = user

    def get_manager(self, request):
        user = self.get_user(request)
        if user:
            return request.application.get_manager(user)
        return None

    def render_template(self, template, request, context):

        unsupported = False
        ua = request.getHeader('User-Agent')
        if ua.find('MSIE 6') > -1:
            unsupported = True

        manager = self.get_manager(request)
        user = self.get_user(request)
        shares = []

        if manager is not None:
            shares = manager.store.find(models.RemoteShare,
                models.RemoteShare.user == user
                ).order_by(expr.Asc(models.RemoteShare.name))

        defaults = {
            'version': VERSION,
            'unsupported': unsupported,
            'user': user,
            'shares': shares
            }

        defaults.update(context);

        try:
            t = request.templateFactory.get_template(template)
        except Exception as e:
            return self.render_template('errors/error.html', request, {
                'title': 'Template Not Found',
                'message': 'Could not load page template: %s' % template
                })

        request.setHeader('Content-type', 'text/html; charset=UTF-8')
        return t.render(defaults).encode('utf8')

class AuthenticatedResource(Resource):

    def render(self, request, *args):
        if not self.is_logged_in(request):
            request.redirect('/account/login')
            request.finish()
            return server.NOT_DONE_YET
        return Resource.render(self, request, *args)

class AdminResource(Resource):

    def render(self, request, *args):
        user = self.get_user(request)
        if not user:
            request.redirect('/account/login')
            request.finish()
            return server.NOT_DONE_YET
        elif not user.admin:
            request.setHeader('Status', '401 Unauthorized')
            return self.render_template('errors/error.html', request, {
                'title': 'Not Authorized',
                'message': 'You are not authorized to view this page'
                })
        return Resource.render(self, request, *args)

class ErrorResource(Resource):

    def __init__(self, status, title, message, *args, **kwargs):
        self.status = status
        self.title = title
        self.message = message
        Resource.__init__(self, *args, **kwargs)

    def render(self, request):
        if self.status:
            request.setHeader('Status', self.status)
        return self.render_template('errors/error.html', request, {
            'title': self.title,
            'message': self.message
            })

class NotFoundResource(ErrorResource):

    def __init__(self, *args, **kwargs):
        ErrorResource.__init__(self, '404 Not Found', 'Not Found',
                'That page does not exist', *args, **kwargs)
