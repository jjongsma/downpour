import os
from storm.locals import *
from downpour2.core.store import schema, User
from downpour2.library import patches

def update_store(store):
    SharingSchema().upgrade(store, checkTable='remote_shares')

class SharingSchema(schema.Schema):

    create_statements = [

        "CREATE TABLE remote_shares (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "name TEXT," +
            "address TEXT," +
            "username TEXT," +
            "password TEXT," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

    ]

    drop_statements = [
        "DROP TABLE remote_shares"
    ]

    delete_statements = [
        "DELETE FROM remote_shares"
    ]

    def __init__(self):
        super(SharingSchema, self).__init__(SharingSchema.create_statements,
            SharingSchema.drop_statements, SharingSchema.delete_statements, patches)

class RemoteShare(object):

    __storm_table__ = 'remote_shares'

    id = Int(primary=True)
    user_id = Int()
    name = Unicode()
    address = Unicode()
    username = Unicode()
    password = Unicode()

    user = Reference(user_id, User.id)
