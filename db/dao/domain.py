from typing import Union

from db.interfaces.dao import Dao
from db.handler import DBHandler
from db.models.domain import Domain


class DomainDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "domains")

    def dao_create_object(self, data):
        return Domain(
                did=data[0],
                name=data[1],
                level=data[2],
                email_format=data[3],
                dns=data[4],
                frontable=data[5],
                takeover=data[6],
                additional_info=data[7]
            )

    def find_by_name_like(self, name):
        name = f"%{name}"
        sql = "SELECT * FROM domains where name LIKE ?"
        args = (name,)
        objects = self.dao_collect(sql, args)
        return objects

    def get_email_format(self, name):
        sql = "SELECT email_format from domains where name = ?"
        args = (name,)
        fmt = self.dao_collect(sql, args)
        return fmt[0] if len(fmt) > 0 else None

    def update_email_format(self, name, email_format):
        if not self.find_by_name(name):
            return False
        sql = "UPDATE domains SET email_format=? WHERE name=?"
        args = (email_format, name,)
        self.dao_execute(sql, args)
        return True

    def find_by_name(self, name) -> Union[Domain, None]:
        sql = "SELECT * FROM domains where name = ?"
        args = (name,)
        objects = self.dao_collect(sql, args)
        return objects[0] if len(objects) > 0 else None

    def find_by_id(self, did: int):
        sql = "SELECT * FROM domains where did = ?"
        args = (did,)
        objects = self.dao_collect(sql, args)
        return objects[0] if len(objects) > 0 else None

    def exists(self, domain: Union[Domain, str]):
        name = domain
        if isinstance(domain, Domain):
            name = domain.name
        return self.find_by_name(name) is not None

    def delete_if_no_dns(self):
        sql = r"""
        DELETE FROM domains where dns = '{"A": null, "AAAA": null, "CNAME": null, "MX": null, "NS": null, "TXT": null}'
        """
        self.dao_execute(sql)
        sql = r"""
        DELETE FROM domains where dns = '{"A": [], "AAAA": [], "CNAME": [], "MX": [], "NS": [], "TXT": []}'
        """
        self.dao_execute(sql)

    def delete(self, domain: Union[Domain, str, int]):
        if isinstance(domain, str):
            domain = self.find_by_name(domain)
        elif isinstance(domain, int):
            domain = self.find_by_id(domain)
        if domain is None:
            return
        sql = "DELETE FROM domains where did = ?"
        args = (domain.did,)
        self.dao_execute(sql, args)

    def update(self, domain: Union[Domain, str]):
        # See if there is already
        if not self.exists(domain):
            return self.save(domain)
        sql = r"""UPDATE domains 
        SET email_format = ?, 
        level = ?, 
        dns = ?, 
        frontable = ?, 
        takeover = ?, 
        additional_info = ?
        WHERE name = ?
        """
        args = (domain.email_format, domain.level, domain.dns_str, domain.frontable_str, domain.takeover_str, domain.additional_info_str, domain.name)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            return True

    def save(self, domain: Domain):
        # See if there is already
        if self.exists(domain):
            return False
        sql = "INSERT OR IGNORE INTO domains (name, email_format, level, dns, frontable, takeover, additional_info) VALUES (?, ?, ?, ?, ?, ?, ?)"
        args = (
            domain.name, domain.email_format, domain.level, domain.dns_str, domain.frontable_str, domain.takeover_str,
            domain.additional_info_str
        )
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
            return True
