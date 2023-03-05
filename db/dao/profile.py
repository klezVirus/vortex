from db.handler import DBHandler
from db.interfaces.dao import Dao
from db.models.profile import Profile
from db.models.user import User


class ProfileDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "profiles")

    def dao_create_object(self, data):
        return Profile(
                    pid=data[0],
                    user=data[1],
                    ptype=data[3],
                    url=data[2],
                )

    def find_by_user(self, uid):
        sql = "SELECT * FROM profiles WHERE uid = ?"
        return self.dao_collect(sql, (uid,))

    def delete(self, profile: Profile):
        sql = "DELETE FROM profiles where id = ?"
        args = (profile.id, )
        self.dao_execute(sql, args)

    def save(self, profile: Profile):
        # See if there is already
        profiles = self.find_by_user(profile.user)
        for p in profiles:
            if p.url == profile.url:
                return

        sql = "INSERT OR IGNORE INTO profiles (uid, ptype, url) VALUES (?, ?, ?)"
        args = (profile.user, profile.ptype, profile.url)
        self.dao_execute(sql, args)
