from twisted.python import components
from zope import interface


class IAccount(interface.Interface):
    pass


class Account(components.Adapter, object):
    interface.implements(IAccount)

    def __init__(self, *args):
        components.Adapter.__init__(self, *args)
        self.user = None
