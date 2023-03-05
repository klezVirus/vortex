from abc import ABC, abstractmethod

from db.handler import DBHandler


class Dao(ABC):
    def __init__(self, handler: DBHandler, table: str):
        self.dbh = handler
        self.__table = table

    def dao_execute(self, sql, args=None):
        with self.dbh.create_cursor() as cursor:
            if args:
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)

    def dao_collect(self, sql, args=None):
        objects = []
        with self.dbh.create_cursor() as cursor:
            if args:
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)
            for data in cursor:
                try:
                    o = self.dao_create_object(data)
                    objects.append(o)
                except:
                    pass
        return objects

    @abstractmethod
    def dao_create_object(self, data):
        pass

    def list_all(self):
        sql = f"SELECT * FROM {self.__table}"
        objects = self.dao_collect(sql)
        return objects if len(objects) > 0 else []

    def exists(self, **kwargs):
        pass


