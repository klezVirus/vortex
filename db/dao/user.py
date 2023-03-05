from db.dao.leak import LeakDao
from db.dao.profile import ProfileDao
from db.handler import DBHandler
from db.interfaces.dao import Dao
from db.models.profile import Profile
from db.models.endpoint import Endpoint
from db.models.user import User
from utils.utils import progress, error


class UserDao(Dao):
    def __init__(self, handler: DBHandler):
        super().__init__(handler, "users")

    def dao_create_object(self, data):
        return User(
                    uid=data[0],
                    name=data[1],
                    email=data[2],
                    role=data[3],
                    valid=data[4]
                )

    def list_all(self):
        users = []
        sql = "SELECT * FROM users"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for data in cursor:
                uid = data[0]
                user = self.dao_create_object(data)
                leaks = []
                sql = "SELECT password FROM leaks where uid = ?"
                args = (uid, )
                with self.dbh.create_cursor() as aux:
                    aux.execute(sql, args)
                    for leak_data in aux:
                        if leak_data[0]:
                            leaks.append(leak_data[0])
                    user.leaks = leaks
                profiles = []
                sql = "SELECT * FROM profiles where uid = ?"
                with self.dbh.create_cursor() as aux:
                    aux.execute(sql, args)
                    for profile_data in aux:
                        profiles.append(Profile(
                            pid=profile_data[0],
                            url=profile_data[1],
                            ptype=profile_data[2],
                            user=profile_data[3]
                        ))
                    user.profiles = profiles
                users.append(user)
        return users

    def exists(self, email):
        sql = "SELECT * from users where email = ?"
        args = (email, )
        users = self.dao_collect(sql, args)
        return len(users) > 0

    def find_by_username(self, username):
        sql = "SELECT * from users where email = ?"
        args = (username, )
        users = self.dao_collect(sql, args)
        return users[0] if len(users) > 0 else None

    def delete(self, user: User):
        sql = "DELETE FROM users where uid = ?"
        args = (user.uid,)
        self.dao_execute(sql, args)

    def set_valid(self, user: User):
        # Finally, update the DB user
        user.valid = True
        self.save(user)

    def save(self, user: User):
        leak_dao = LeakDao(handler=self.dbh)
        profile_dao = ProfileDao(handler=self.dbh)

        # First, check if the user exists
        db_user = self.find_by_username(user.email)
        if not db_user:
            sql = "INSERT OR IGNORE INTO users (name, email, job) VALUES (?, ?, ?)"
            args = (user.name, user.email, user.role)
            with self.dbh.create_cursor() as cursor:
                cursor.execute(sql, args)
            # Now, we can fetch the User
            db_user = self.find_by_username(user.email)
        else:
            error(f"{db_user.email} already in the DB")
        # Eventually, we merge the users
        db_user.update(user)

        # Check for leaks
        if len(db_user.leaks) > 0:
            for leak in db_user.leaks:
                leak.uid = db_user.uid
                leak_dao.save(leak)

        # Check for profiles
        if len(db_user.profiles) > 0:
            for profile in db_user.profiles:
                profile.uid = db_user.uid
                profile_dao.save(profile)

        # Finally, update the DB user
        sql = r"""UPDATE users 
        SET name = ?,
            email = ?,
            job = ?,
            valid = ?
        WHERE
            uid = ?
        """
        args = (db_user.name, db_user.email, db_user.role, db_user.uid, db_user.valid)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)
        return db_user.uid


