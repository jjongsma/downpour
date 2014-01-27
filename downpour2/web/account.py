from downpour2.core import util
from downpour2.web import common, auth


class Root(common.AuthenticatedResource):

    def __init__(self, application, environment):

        super(Root, self).__init__(application, environment)

        self.putChild('', self)
        self.putChild('detail', Detail(self.application, self.environment))
        self.putChild('login', Login(self.application, self.environment))
        self.putChild('logout', Logout(self.application, self.environment))
        self.putChild('save', Save(self.application, self.environment))

    def render_GET(self, request):
        return self.render_json(self.get_user(request))


class Detail(common.RoutedResource):

    def render_GET(self, request):
        user = self.get_user(request)
        if user is not None:
            return self.render_json(user, util.StormModelEncoder)
        else:
            return self.render_json_error(request, 403, 'Not authenticated')


class Login(common.RoutedResource):

    def render_POST(self, request):
        username = unicode(request.args['username'][0])
        password = unicode(request.args['password'][0])
        user = self.application.users.login(username, password)
        if user:
            self.set_user(user, request)
            return self.render_json(user, util.StormModelEncoder)
        else:
            return self.render_json_error(request, 401, 'Invalid username or password')


class Logout(common.Resource):

    def render_GET(self, request):
        self.set_user(None, request)
        return self.render_json({'success': True})


class Save(common.AuthenticatedResource):

    def render_POST(self, request):
        newpass = request.args.get('new_password', (None,))[0]
        newpass2 = request.args.get('confirm_password', (None,))[0]
        sharepass = request.args.get('share_password', (None,))[0]
        errors = ''
        if newpass is not None and newpass != '':
            if newpass2 is None or newpass2 == '':
                errors = ''.join((errors, 'Confirm password is empty'))
            if newpass != newpass2:
                errors = ''.join((errors, 'Passwords do not match'))
        if len(errors) > 0:
            request.setResponseCode(400, 'Could not save account')
            return self.render_json({'errors': errors})
        else:
            account = request.getSession(auth.IAccount)
            if newpass is not None and newpass != '':
                account.user.password = unicode(newpass)
            if sharepass is not None and sharepass != '':
                account.user.share_password = unicode(sharepass)
            manager = self.get_manager(request)
            # Save to database
            manager.store.commit()
            return self.render_json(account.user, util.StormModelEncoder)
