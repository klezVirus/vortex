import sqlite3
import sqlite3 as sql
import traceback
from sqlite3 import Connection, Cursor

from utils.utils import get_project_root, generate_string


class DBCursor:
    def __init__(self, db):
        self.db = db
        self.connection: Connection = None
        self.cursor: Cursor = None

    def __enter__(self):
        self.connection = sql.connect(self.db)
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, tb):
        self.connection.commit()
        self.connection.close()
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
        return True

    def commit(self):
        self.connection.commit()

    def execute(self, sql, *args, **kwargs):
        self.cursor.execute(sql, *args, **kwargs)

    def execute_many(self, sql, values: list):
        self.cursor.executemany(sql, values)


class DBHandler:
    def __init__(self, workspace):
        self.db = get_project_root().joinpath("data").joinpath("workspaces").joinpath(f"{workspace}.db")
        self.workspace = workspace
        self.connection: Connection = None
        self.__callback = None

    def enable_debug(self, callback=None):
        if not callback:
            self.__callback = print
            return
        self.__callback = callback

    def disable_debug(self):
        self.__callback = None

    def db_exists(self):
        return self.db.exists()

    def db_initialised(self):
        if not self.db_exists():
            return False
        self.connect()
        success = True
        try:
            self.execute("SELECT * FROM `users` LIMIT 1", ())
        except sqlite3.OperationalError:
            success = False
        self.tear_down()
        return success

    def connect(self):
        self.connection = sql.connect(self.db)
        self.connection.set_trace_callback(self.__callback)

    def tear_down(self):
        self.close()

    def close(self):
        if self.connection:
            self.connection.close()
        self.connection = None

    def create_cursor(self) -> DBCursor:
        if self.connection:
            self.close()
        cursor = DBCursor(self.db)
        if cursor and cursor.connection:
            cursor.connection.set_trace_callback(self.__callback)
        elif cursor and cursor.cursor and cursor.cursor.connection:
            cursor.cursor.connection.set_trace_callback(self.__callback)
        return cursor

    def execute(self, sql, args=None):
        if not self.connection:
            self.connect()
        return self.connection.execute(sql, args)

    def get_email_format(self):
        fmt = None
        sql = "SELECT email_format from config where cid = 1"
        with self.create_cursor() as cursor:
            cursor.execute(sql)
            for data in cursor:
                if len(data) > 0:
                    fmt = data[0]
        return fmt

    def set_email_format(self, mail_format):
        sql = "INSERT OR REPLACE INTO config(cid, email_format, aws_prefix) values (?, ?, ?)"
        args = (1, mail_format, generate_string(5))
        with self.create_cursor() as cursor:
            cursor.execute(sql, args)

    def search_profiles_by_uid(self, user):
        sql = "SELECT * FROM profiles WHERE uid LIKE ?"
        args = (user, )
        self.connection.execute(sql, args)

    def search_profiles_by_type(self, ptype):
        sql = "SELECT * FROM profiles WHERE ptype = ?"
        args = (ptype, )
        self.connection.execute(sql, args)
