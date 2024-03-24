import sqlite3
import os
import shutil
import traceback
from cave.libcave.video import Video
from cave.libcave.videoutils import hash_video
from misc.log import with_logging
from cave.libcave.sql import SqlClass

DATABASE_VERSION = 2

class DBInfo(SqlClass):
    @classmethod
    def table_setup(cls):
        cls.table_name = "dbinfo"
        cls.c.execute("""CREATE TABLE IF NOT EXISTS %s (
                         id               INTEGER PRIMARY KEY,
                         version          INTEGER
                         )""" % cls.table_name)
        cls.commit()
        if len(cls.get_all()) == 0:
            new = cls.new(version=DATABASE_VERSION)

    @classmethod
    def get_version(cls):
        return cls.get_all()[0].version
    
    @classmethod
    def set_version(cls, v):
        q = cls.get_all()[0]
        q.version = v
        q.update()

@with_logging
class Database:
    
    def __init__(self, filename):
        if filename is None:
            self.log.warning("Invalid database filename specified")
            self.error = True
            return None

        try:
            self.conn = sqlite3.connect(filename, check_same_thread=False, isolation_level="EXCLUSIVE")
        except sqlite3.OperationalError:
            self.log.error("Failed to open database file: %s" % filename)
            self.error = True
            return None

        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()

        self.c.execute("PRAGMA synchronous = 0")
        self.c.execute("PRAGMA journal_mode = OFF")

        self.filename = os.path.abspath(filename)
        self.root_dir = os.path.dirname(self.filename)

        DBInfo.link_sqlite(self)
        Video.link_sqlite(self)

        db_version = DBInfo.get_version()
        if db_version > DATABASE_VERSION:
            # Handle error or other specific behavior for unexpected versions
            pass

        if db_version != DATABASE_VERSION:
            # Handle upgrades or specific behavior for different versions
            pass

        self.log.info("Database linked to %s" % filename)
        self.error = False

    def get_filename(self):
        return self.filename

    def get_relative_path(self, abspath):
        abspath = os.path.abspath(abspath)
        if os.path.commonprefix([abspath, self.root_dir]) != self.root_dir:
            self.log.error("File chosen outside of root database directory")
            return
        return os.path.relpath(abspath, self.root_dir)

    def get_absolute_path(self, relpath):
        return os.path.join(self.root_dir, relpath)