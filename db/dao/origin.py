from typing import Union

from db.handler import DBHandler
from db.interfaces.dao import Dao
from db.models.etype import Etype
from db.models.origin import Origin
from db.models.profile import Profile
from db.models.endpoint import Endpoint


class OriginDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "origins")

    def dao_create_object(self, data):
        o = Origin(
            oid=data[0],
            host=data[1],
            port=data[2],
            ssl=data[3],
            up=data[4]
        )
        return o

    def delete(self, origin: Origin):
        sql = "DELETE FROM origins where oid = ?"
        args = (origin.oid,)
        self.dao_execute(sql, args)

    def find_by_host_like(self, host):
        host = f"%{host}%"
        sql = "SELECT * FROM origins where host LIKE ?"
        args = (host,)
        return self.dao_collect(sql, args)

    def find_by_host_port(self, host, port):
        sql = "SELECT * FROM origins where host = ? and port = ?"
        args = (host, port,)
        return self.dao_collect(sql, args)

    def find_by_host(self, host):
        sql = "SELECT * FROM origins where host = ?"
        args = (host,)
        return self.dao_collect(sql, args)

    def exists(self, origin: Union[Origin, str]):
        if isinstance(origin, Origin):
            host, port = origin.host, origin.port
        elif isinstance(origin, str):
            host, port = origin.split(":")
        else:
            raise TypeError("Expected Origin or str")
        result = self.find_by_host_port(host, port)
        return result is not None and len(result) > 0

    def save(self, origin: Origin):
        # See if there is already
        if self.exists(origin):
            return
        sql = "INSERT OR IGNORE INTO origins (host, port, ssl, up) VALUES (?, ?, ?, ?)"
        args = (origin.host, origin.port, origin.ssl, origin.up,)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
