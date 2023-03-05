from db.interfaces.dao import Dao
from db.handler import DBHandler
from db.models.etype import Etype


class EtypeDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "etypes")
        self.fallback = 0

    def dao_create_object(self, data):
        return Etype(
            etid=data[0],
            name=data[1],
            is_vpn=data[2],
            is_office=data[3],
            is_o365=data[4]
        )

    def default(self):
        sql = "SELECT * FROM etypes where name = 'UNKNOWN'"
        etypes = self.dao_collect(sql)
        return etypes[0]  # Must be one or we just throw an error here

    def delete(self, etype: Etype):
        sql = "DELETE FROM etypes where etid = ?"
        args = (etype.etid,)
        self.dao_execute(sql, args)

    def find_by_name(self, name):
        sql = "SELECT * FROM etypes where name = ?"
        args = (name,)
        etypes = self.dao_collect(sql, args)
        return etypes[0] if len(etypes) > 0 else self.fallback

    def find_by_id(self, id):
        sql = "SELECT * FROM etypes where etid = ?"
        args = (id,)
        etypes = self.dao_collect(sql, args)
        return etypes[0] if len(etypes) > 0 else self.fallback

    def save(self, e: Etype):
        # See if there is already
        if self.find_by_name(e.name):
            return
        sql = "INSERT OR IGNORE INTO etypes (name, is_vpn, is_office, is_o365) VALUES (?, ?, ?, ?)"
        args = (e.name, e.is_vpn, e.is_office, e.is_o365)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
