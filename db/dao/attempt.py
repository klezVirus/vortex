from db.interfaces.dao import Dao
from db.handler import DBHandler
from db.models.attempt import Attempt


class AttemptDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "attempts")

    def dao_create_object(self, data):
        return Attempt(
                    attempt_id=data[0],
                    user_id=data[1],
                    etype_ref=data[2],
                    realm=data[3],
                    group=data[4],
                    username=data[5],
                    password=data[6],
                    url=data[7],
                    created_at=data[8]
                )

    def exists(self, username, password, url):
        sql = "SELECT * FROM attempts WHERE url = ? AND username = ? AND password = ?"
        args = (url, username, password)
        return len(self.dao_collect(sql, args)) > 0

    def clear(self):
        sql = "DELETE FROM attempts WHERE attempt_id <> 0"
        self.dao_execute(sql)

    def delete(self, obj: Attempt):
        sql = "DELETE FROM attempts where attempt_id = ?"
        args = (obj.attempt_id,)
        self.dao_execute(sql, args)

    def save(self, obj: Attempt):
        # See if there is already
        if self.exists(obj.username, obj.password, obj.url):
            return
        sql = "INSERT OR IGNORE INTO attempts (user_id, etype_ref, username, password, url, vgroup, realm) VALUES (?, ?, ?, ?, ?, ?, ?)"
        args = (obj.user_id, obj.etype_ref, obj.username, obj.password, obj.url, obj.group, obj.realm)
        self.dao_execute(sql, args)

    def save_new(self, user_id, etype_ref, username, password, url, realm="", group=""):
        login = Attempt(attempt_id=0, user_id=user_id, etype_ref=etype_ref, username=username, password=password,
                        url=url, realm=realm, group=group)
        self.save(login)
