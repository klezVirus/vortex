from db.handler import DBHandler
from db.models.profile import Profile
from db.models.user import User


class ProfileDao:
    def __init__(self, handler: DBHandler):
        self.dbh = handler

    def list_all(self):
        profiles = []
        sql = "SELECT * FROM profiles"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for i in range(cursor.rowcount):
                data = cursor.fetchone()
                profile = Profile(
                    pid=data[0],
                    user=data[1],
                    ptype=data[3],
                    url=data[2],
                )
                profiles.append(profile)
        return profiles

    def find_by_user(self, uid):
        profiles = []
        sql = "SELECT * FROM profiles WHERE uid = ?"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, uid)
            for i in range(cursor.rowcount):
                data = cursor.fetchone()
                profile = Profile(
                    pid=data[0],
                    user=data[1],
                    ptype=data[3],
                    url=data[2],
                )
                profiles.append(profile)
        return profiles

    def delete(self, profile: Profile):
        sql = "DELETE FROM profiles where id = ?"
        args = (profile.id, )
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def save(self, profile: Profile):
        # See if there is already
        profiles = self.find_by_user(profile.user)
        for p in profiles:
            if p.url == profile.url:
                return

        sql = "INSERT OR IGNORE INTO profiles (uid, ptype, url) VALUES (?, ?, ?)"
        args = (profile.user, profile.ptype, profile.url)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
