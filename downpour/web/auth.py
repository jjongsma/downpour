from downpour.core import models
from twisted.python import components
from twisted.web import server
from zope import interface

class IAccount(interface.Interface):
    pass

class Account(components.Adapter):
    interface.implements(IAccount)

    def __init__(self, *args):
        components.Adapter.__init__(self, *args)
        self.user = None
