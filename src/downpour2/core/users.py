from downpour2.core.store import models

class UserManager:

    def __init__(self, store):

        self.store = store;

    def login(self, username, password):

        user = self.store.find(models.User,
            models.User.username == username,
            models.User.password == password).one()

        return user

    def get(self, username):

        user = self.store.find(models.User,
            models.User.username == username).one()

        return user
