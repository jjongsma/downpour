from storm.locals import *
from downpour2.core import store


class AlertManager(object):
    def __init__(self, _store):
        self.store = _store

    def all(self, user):
        return self.store.find(
            store.Alert,
            store.Alert.user == user
        ).order_by(Desc(store.Alert.timestamp))

    def unread(self, user):
        return self.store.find(
            store.Alert,
            store.Alert.user == user,
            store.Alert.viewed == False
        ).order_by(Desc(store.Alert.timestamp))

    def view(self, alert):
        alert.viewed = True
        self.store.add(alert)
        self.store.commit()

    def add(self, alert):
        self.store.add(alert)
        self.store.commit()
