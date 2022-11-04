import json

from db.handler import DBHandler
from db.models.domain import Domain
from db.models.profile import Profile
from db.models.endpoint import Endpoint


class DomainDao:
    def __init__(self, handler: DBHandler):
        self.dbh = handler

    def list_all(self):
        domains = []
        sql = "SELECT * FROM domains"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for data in cursor:
                domain = Domain(
                    did=data[0],
                    name=data[1],
                    level=data[2],
                    email_format=data[3],
                    additional_info=data[4]
                )
                domains.append(domain)
        return domains

    def find_by_name_like(self, name):
        name = f"%{name}"
        sql = "SELECT * FROM domains where name LIKE ?"
        args = (name,)
        ds = []
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            for data in cursor:
                d = Domain(
                    did=data[0],
                    name=data[1],
                    level=data[2],
                    email_format=data[3],
                    additional_info=data[4]
                )
                ds.append(d)
        return ds

    def get_email_format(self, name):
        fmt = None
        sql = "SELECT email_format from domains where name = ?"
        args = (name,)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            for data in cursor:
                if len(data) > 0:
                    fmt = data[0]
        return fmt

    def update_email_format(self, name, email_format):
        sql = "UPDATE domains SET email_format=? WHERE name=?"
        args = (email_format, name,)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def find_by_name(self, name):
        sql = "SELECT * FROM domains where name = ?"
        args = (name,)
        ds = []
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            for data in cursor:
                d = Domain(
                    did=data[0],
                    name=data[1],
                    level=data[2],
                    email_format=data[3],
                    additional_info=data[4]
                )
                ds.append(d)
        return ds[0] if len(ds) > 0 else None

    def exists(self, domain: Domain):
        return self.find_by_name(domain.name) is not None

    def delete(self, domain: Domain):
        sql = "DELETE FROM domains where did = ?"
        args = (domain.did,)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def save(self, domain: Domain):
        # See if there is already
        if self.exists(domain):
            return False
        sql = "INSERT OR IGNORE INTO domains (name, email_format, level, additional_info) VALUES (?, ?, ?, ?)"
        args = (domain.name, domain.email_format, domain.level, domain.additional_info_str)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            return True
