from downpour2.core import store

class UserManager:

    def __init__(self, store):

        self.store = store;

    def login(self, username, password):

        user = self.store.find(store.User,
            store.User.username == username,
            store.User.password == password).one()

        return user

    def get(self, id=None, username=None):

        user = None

        if username is not None:
            user = self.store.find(store.User,
                store.User.username == username).one()
        elif id is not None:
            user = self.store.find(store.User,
                store.User.id == id).one()

        return user

    def delete(self, id):
        self.store.remove(self.get(id))

    def save(self, user):
        self.store.add(user)
        selt.store.commit()
