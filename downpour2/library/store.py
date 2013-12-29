from storm.locals import *
from downpour2.core.store import schema, User, Transfer
from downpour2.library import patches

def update_store(store):
    LibrarySchema().upgrade(store, checkTable='libraries')

class LibrarySchema(schema.Schema):

    create_statements = [

        "CREATE TABLE libraries (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "media_type TEXT," +
            "directory TEXT," +
            "pattern TEXT," +
            "keepall BOOLEAN," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")",

        "CREATE TABLE files (" +
            "id INTEGER PRIMARY KEY," +
            "user_id INTEGER," +
            "directory TEXT," +
            "filename TEXT," +
            "size INTEGER," +
            "media_type TEXT," +
            "mime_type TEXT," +
            "transfer_id INTEGER," +
            "original_filename TEXT," +
            "description TEXT," +
            "added INTEGER," +
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,"
            "FOREIGN KEY(transfer_id) REFERENCES transfers(id) ON DELETE CASCADE ON UPDATE CASCADE"
            ")"

    ]

    drop_statements = [
        "DROP TABLE files",
        "DROP TABLE libraries"
    ]

    delete_statements = [
        "DELETE FROM files",
        "DELETE FROM libraries"
    ]

    def __init__(self):
        super(LibrarySchema, self).__init__(LibrarySchema.create_statements,
            LibrarySchema.drop_statements, LibrarySchema.delete_statements, patches)

class Library(object):

    __storm_table__ = 'libraries'

    id = Int(primary=True)
    user_id = Int()
    media_type = Unicode()
    directory = Unicode()
    pattern = Unicode()
    keepall = Bool()

    user = Reference(user_id, User.id)

class File(object):

    __storm_table__ = 'files'

    id = Int(primary=True)
    user_id = Int()
    directory = Unicode()
    filename = Unicode()
    size = Int()
    media_type = Unicode()
    mime_type = Unicode()
    transfer_id = Int()
    original_filename = Unicode()
    description = Unicode()
    added = Int()

    user = Reference(user_id, User.id)
    transfer = Reference(transfer_id, Transfer.id)

Transfer.files = ReferenceSet(Transfer.id, File.transfer_id)
