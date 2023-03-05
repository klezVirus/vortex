from typing import Union

from db.interfaces.dao import Dao
from db.handler import DBHandler
from db.models.endpoint import Endpoint


class EndpointDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "endpoints")

    def dao_create_object(self, data):
        return Endpoint(
            eid=data[0],
            target=data[1],
            email_format=data[2],
            etype_ref=data[3],
            additional_info=data[4]
        )

    def delete(self, endpoint: Endpoint):
        sql = "DELETE FROM endpoints where eid = ?"
        args = (endpoint.eid,)
        self.dao_execute(sql, args)

    def find_by_name_like(self, name):
        name = f"%{name}%"
        sql = "SELECT * FROM endpoints where target LIKE ?"
        args = (name,)
        return self.dao_collect(sql, args)

    def find_by_name_and_type(self, name, etype):
        sql = "SELECT * FROM endpoints where target = ? and etype_ref = ?"
        args = (name, etype,)
        return self.dao_collect(sql, args)

    def get_email_format(self, origin):
        sql = "SELECT * FROM endpoints where target = ?"
        args = (origin,)
        result = self.dao_collect(sql, args)
        return result[0].email_format if len(result) > 0 else None

    def find_where_text(self, text):
        text = f"%{text}%"
        sql = "SELECT * FROM endpoints where additional_info LIKE ?"
        args = (text,)
        result = self.dao_collect(sql, args)
        return result[0] if len(result) > 0 else None

    def exists_categorised(self, name: Union[Endpoint, str]):
        if isinstance(name, Endpoint):
            name = name.target
        e = self.find_by_name(name)
        return e is not None and e.etype_ref != 1

    def exists(self, name):
        return self.find_by_name(name) is not None

    def find_by_name(self, name):
        sql = "SELECT * FROM endpoints where target = ?"
        args = (name,)
        result = self.dao_collect(sql, args)
        return result[0] if len(result) > 0 else None

    def update(self, endpoint: Endpoint):
        if not self.exists(endpoint.target):
            self.save(endpoint)
            return
        db_entry = self.find_by_name(endpoint.target)
        if db_entry.etype_ref != 1 and endpoint.etype_ref == 1:
            return
        sql = r"""UPDATE endpoints 
        SET target = ?, 
            email_format = ?, 
            etype_ref = ?, 
            additional_info = ?
        WHERE eid = ?
"""
        args = (endpoint.target, endpoint.email_format, endpoint.etype_ref, endpoint.additional_info_str, db_entry.eid)
        with self.dbh.create_cursor() as cursor:
                cursor.execute(sql, args)

    def save(self, endpoint: Endpoint):
        # See if there is already
        if self.exists(endpoint.target):
            self.update(endpoint)
            return
        sql = "INSERT OR IGNORE INTO endpoints (target, email_format, etype_ref, additional_info) VALUES (?, ?, ?, ?)"
        args = (endpoint.target, endpoint.email_format, endpoint.etype_ref, endpoint.additional_info_str)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
