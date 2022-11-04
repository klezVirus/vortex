from db.handler import DBHandler
from db.models.login import Login


class LoginDao:
    def __init__(self, handler: DBHandler):
        self.dbh = handler

    def list_all(self):
        logins = []
        sql = "SELECT * FROM found_logins"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for i in range(cursor.rowcount):
                data = cursor.fetchone()
                login = Login(
                    login_id=data[0],
                    email=data[1],
                    password=data[2],
                    url=data[3]
                )
                logins.append(login)
        return logins

    def find_by_email_password_url(self, email, password, url):
        logins = []
        sql = "SELECT * FROM found_logins WHERE email = ? AND password = ? AND url = ?"
        with self.dbh.create_cursor() as cursor:
            args = (email, password, url)
            cursor.execute(sql, args)
            for i in range(cursor.rowcount):
                data = cursor.fetchone()
                login = Login(
                    login_id=data[0],
                    email=data[1],
                    password=data[2],
                    url=data[3]
                )
                logins.append(login)
        return logins

    def delete(self, login: Login):
        sql = "DELETE FROM leaks where login_id = ?"
        args = (login.login_id, )
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def save(self, login: Login):
        # See if there is already
        logins = self.find_by_email_password_url(login.email, login.password, login.url)
        for p in logins:
            if p.password == login.password:
                return

        sql = "INSERT OR IGNORE INTO found_logins (email, password, url) VALUES (?, ?, ?)"
        args = (login.email, login.password, login.url)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def save_new(self, email, password, url):
        login = Login(login_id=0, email=email, password=password, url=url)
        self.save(login)