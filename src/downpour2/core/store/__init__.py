import os
from storm.locals import Store, create_database
from downpour2.core.store import schema, sqlitefk

def get_store(config=None):

    db_path = os.path.expanduser(config.value(('downpour', 'state')))

    if not os.access(db_path, os.F_OK):
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir);

    database = create_database('sqlite:%s' % db_path)
    store = Store(database)

    schema.DownpourSchema().upgrade(store)

    return store;
