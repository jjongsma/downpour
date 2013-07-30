from storm.databases.sqlite import SQLite
from storm.databases import Dummy
import storm.database

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    try:
        from sqlite3 import dbapi2 as sqlite
    except ImportError:
        sqlite = Dummy

class SQLiteFK(SQLite):

    def __init__(self, uri):
        SQLite.__init__(self, uri)

    def raw_connect(self):
        # See the story at the end to understand why we set isolation_level.
        raw_connection = sqlite.connect(self._filename, timeout=self._timeout,
            isolation_level=None)
        if self._synchronous is not None:
            raw_connection.execute("PRAGMA synchronous = %s" %
                (self._synchronous,))

        # enable foreign keys
        raw_connection.execute("PRAGMA foreign_keys = ON;")

        return raw_connection

storm.database.register_scheme("sqlite", SQLiteFK)
