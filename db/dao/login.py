from db.interfaces.dao import Dao
from db.handler import DBHandler
from db.models.login import Login


class LoginDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "found_logins")

    def dao_create_object(self, data):
        return Login(
            login_id=data[0],
            realm=data[1],
            group=data[2],
            email=data[3],
            password=data[4],
            eid=data[5]
        )

    def exists(self, email, password, eid):
        return len(self.find_by_email_password_url(email, password, eid)) > 0

    def find_by_email_password_url(self, email, password, eid):
        sql = "SELECT * FROM found_logins WHERE email = ? AND password = ? AND eid = ?"
        args = (email, password, eid)
        return self.dao_collect(sql, args)

    def delete(self, login: Login):
        sql = "DELETE FROM leaks where login_id = ?"
        args = (login.login_id,)
        self.dao_execute(sql, args)

    def save(self, login: Login):
        # See if there is already
        if self.exists(login.email, login.password, login.eid):
            return
        sql = "INSERT OR IGNORE INTO found_logins (email, password, eid) VALUES (?, ?, ?)"
        args = (login.email, login.password, login.eid)
        self.dao_execute(sql, args)

    def save_new(self, email, password, eid):
        login = Login(login_id=0, email=email, password=password, eid=eid)
        self.save(login)
