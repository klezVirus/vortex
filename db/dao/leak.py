from db.handler import DBHandler
from db.models.leak import Leak
from db.models.profile import Profile
from db.models.user import User


class LeakDao:
    def __init__(self, handler: DBHandler):
        self.dbh = handler

    def list_all(self):
        leaks = []
        sql = "SELECT * FROM leaks"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for i in range(cursor.rowcount):
                data = cursor.fetchone()
                leak = Leak(
                    leak_id=data[0],
                    uid=data[1],
                    password=data[2],
                    hashed=data[3],
                    address=data[4],
                    phone=data[5],
                    database=data[6]
                )
                leaks.append(leak)
        return leaks

    def find_by_user(self, uid):
        leaks = []
        sql = "SELECT * FROM leaks WHERE uid = ?"
        with self.dbh.create_cursor() as cursor:
            args = (uid, )
            cursor.execute(sql, args)
            for i in range(cursor.rowcount):
                data = cursor.fetchone()
                leak = Leak(
                    leak_id=data[0],
                    uid=data[1],
                    password=data[2],
                    hashed=data[3],
                    address=data[4],
                    phone=data[5],
                    database=data[6]
                )
                leaks.append(leak)
        return leaks

    def delete(self, leak: Leak):
        sql = "DELETE FROM leaks where leak_id = ?"
        args = (leak.leak_id, )
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def save(self, leak: Leak):
        # See if there is already
        leaks = self.find_by_user(leak.uid)
        for p in leaks:
            if p.password == leak.password:
                return
        sql = "INSERT OR IGNORE INTO leaks (uid, password, hash, address, phone, database) VALUES (?, ?, ?, ?, ?, ?)"
        args = (leak.uid, leak.password, leak.hashed, leak.address, leak.phone, leak.database)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
