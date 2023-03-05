from db.handler import DBHandler
from db.interfaces.dao import Dao
from db.models.leak import Leak


class LeakDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "leaks")
        self.fallback = 0

    def dao_create_object(self, data):
        return  Leak(
                    leak_id=data[0],
                    uid=data[1],
                    password=data[2],
                    hashed=data[3],
                    address=data[4],
                    phone=data[5],
                    database=data[6]
                )

    def exists(self, user_id):
        return len(self.find_by_user(user_id)) > 0

    def find_by_user(self, uid):
        sql = "SELECT * FROM leaks WHERE uid = ?"
        args = (uid,)
        return self.dao_collect(sql, args)

    def delete(self, leak: Leak):
        sql = "DELETE FROM leaks where leak_id = ?"
        args = (leak.leak_id, )
        self.dao_execute(sql, args)

    def save(self, leak: Leak):
        # See if there is already
        leaks = self.find_by_user(leak.uid)
        for p in leaks:
            if p.password == leak.password:
                return
        sql = "INSERT OR IGNORE INTO leaks (uid, password, hash, address, phone, database) VALUES (?, ?, ?, ?, ?, ?)"
        args = (leak.uid, leak.password, leak.hashed, leak.address, leak.phone, leak.database)
        self.dao_execute(sql, args)
