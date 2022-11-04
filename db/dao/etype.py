from db.handler import DBHandler
from db.models.etype import Etype
from db.models.profile import Profile
from db.models.endpoint import Endpoint


class EtypeDao:
    def __init__(self, handler: DBHandler):
        self.dbh = handler
        self.fallback = self.default()

    def list_all(self):
        endpoints = []
        sql = "SELECT * FROM etypes"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for data in cursor:
                endpoint = Etype(
                    etid=data[0],
                    name=data[1],
                    is_vpn=data[2],
                    is_office=data[3],
                    is_o365=data[4]
                )
                endpoints.append(endpoint)
        return endpoints

    def default(self):
        sql = "SELECT * FROM etypes where name = 'UNKNOWN'"
        etypes = []
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for data in cursor:
                etype = Etype(
                    etid=data[0],
                    name=data[1],
                    is_vpn=data[2],
                    is_office=data[3],
                    is_o365=data[4]
                )
                etypes.append(etype)
        return etypes[0]  # Must be one or we just throw an error here

    def delete(self, etype: Etype):
        sql = "DELETE FROM etypes where etid = ?"
        args = (etype.etid,)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def find_by_name(self, name):
        sql = "SELECT * FROM etypes where name = ?"
        args = (name,)
        etypes = []
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            for data in cursor:
                etype = Etype(
                    etid=data[0],
                    name=data[1],
                    is_vpn=data[2],
                    is_office=data[3],
                    is_o365=data[4]
                )
                etypes.append(etype)
        return etypes[0] if len(etypes) > 0 else self.fallback

    def find_by_id(self, id):
        sql = "SELECT * FROM etypes where etid = ?"
        args = (id,)
        etypes = []
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            for data in cursor:
                etype = Etype(
                    etid=data[0],
                    name=data[1],
                    is_vpn=data[2],
                    is_office=data[3],
                    is_o365=data[4]
                )
                etypes.append(etype)
        return etypes[0] if len(etypes) > 0 else self.fallback

    def save(self, e: Etype):
        # See if there is already
        if self.find_by_name(e.name):
            return
        sql = "INSERT OR IGNORE INTO etypes (name, is_vpn, is_office, is_o365) VALUES (?, ?, ?, ?)"
        args = (e.name, e.is_vpn, e.is_office, e.is_o365)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
