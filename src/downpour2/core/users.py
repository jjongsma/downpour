from downpour2.core import store

class UserManager:

    def __init__(self, store):

        self.store = store;

    def login(self, username, password):

        user = self.store.find(store.User,
            store.User.username == username,
            store.User.password == password).one()

        return user

    def get(self, username):

        user = self.store.find(store.User,
            store.User.username == username).one()

        return user
