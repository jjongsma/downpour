from downpour.core import models
from downpour.web import common, auth
from twisted.web import server
import hashlib

class Root(common.AuthenticatedResource):

    def __init__(self):
        common.AuthenticatedResource.__init__(self)
        self.putChild('', self)
        self.putChild('login', Login())
        self.putChild('logout', Logout())
        self.putChild('edit', Edit())
        self.putChild('save', Save())
        self.putChild('saved', Saved())

    def render_GET(self, request):
        context = {'title': 'My Account'}
        return self.render_template('account/index.html', request, context)

class Login(common.Resource):

    def render_GET(self, request):
        referrer = request.getHeader('Referer')
        if referrer is not None and referrer.find('//') > -1:
            start = referrer.find('/', referrer.find('//') + 2)
            referrer = referrer[start:]
        context = {'title': 'Login', 'redirect': referrer}
        if 'logout' in request.args:
            context['message'] = 'You have been logged out.'
        return self.render_template('account/login.html', request, context)

    def render_POST(self, request):
        username = unicode(request.args['username'][0]);
        password = unicode(request.args['password'][0]);
        user = request.application.get_user(username, password)
        if user:
            self.set_user(user, request)
            redirect = '/'
            """
            if 'redirect' in request.args and not request.args['redirect'][0].startswith('/account'):
                redirect = request.args['redirect'][0]
            """
            request.redirect(redirect)
            request.finish()
            return server.NOT_DONE_YET
        else:
            context = {'title': 'Login', 'error': 'Invalid username or password'}
            return self.render_template('account/login.html', request, context)

class Logout(common.Resource):

    def render_GET(self, request):
        self.set_user(None, request);
        request.redirect('/account/login?logout=1')
        request.finish()
        return server.NOT_DONE_YET

class Edit(common.AuthenticatedResource):

    def render_GET(self, request):
        context = {'title': 'Update My Account'}
        return self.render_template('account/edit.html', request, context)

class Save(common.AuthenticatedResource):

    def render_POST(self, request):
        newpass = request.args.get('new_password', (None,))[0]
        newpass2 = request.args.get('confirm_password', (None,))[0]
        sharepass = request.args.get('share_password', (None,))[0]
        errors = ''
        if newpass is not None and newpass != '':
            if newpass2 is None or newpass2 == '':
                errors = ''.join((errors, '<li>Confirm password is empty</li>'))
            if newpass != newpass2:
                errors = ''.join((errors, '<li>Passwords do not match</li>'))
        if len(errors) > 0:
            context = {'title': 'Update My Account', 'error': errors}
            return self.render_template('account/edit.html', request, context)
        else:
            account = request.getSession(auth.IAccount)
            if newpass is not None and newpass != '':
                account.user.password = unicode(newpass)
            if sharepass is not None and sharepass != '':
                account.user.share_password = unicode(sharepass)
            manager = self.get_manager(request)
            # Save to database
            manager.store.commit()
            request.redirect('/account/saved')
            request.finish()
            return server.NOT_DONE_YET

class Saved(common.AuthenticatedResource):

    def render_GET(self, request):
        context = {'title': 'Account Saved'}
        return self.render_template('account/saved.html', request, context)
