from db.dao.leak import LeakDao
from db.dao.profile import ProfileDao
from db.handler import DBHandler
from db.models.profile import Profile
from db.models.endpoint import Endpoint
from db.models.user import User
from utils.utils import progress


class UserDao:
    def __init__(self, handler: DBHandler):
        self.dbh = handler

    def list_all(self):
        users = []
        sql = "SELECT * FROM users"
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql)
            for data in cursor:
                uid = data[0]
                user = User(
                    uid=uid,
                    name=data[1],
                    username=data[2],
                    email=data[3],
                    role=data[4],
                    valid=data[5]
                )
                leaks = []
                sql = "SELECT password FROM leaks where uid = ?"
                args = (uid, )
                with self.dbh.create_cursor() as aux:
                    aux.execute(sql, args)
                    for leak_data in aux:
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

    def find_by_username(self, username):
        sql = "SELECT * from users where email = ?"
        args = (username, )
        cursor = self.dbh.execute(sql, args)
        try:
            data = cursor.fetchone()
            return User(
                uid=data[0],
                name=data[1],
                username=data[2],
                email=data[3],
                role=data[4],
                valid=data[5]
            )
        except (IndexError, TypeError):
            # The user doesn't exists
            return None

    def delete(self, user: User):
        sql = "DELETE FROM users where uid = ?"
        args = (user.uid,)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)

    def save(self, user: User):
        leak_dao = LeakDao(handler=self.dbh)
        profile_dao = ProfileDao(handler=self.dbh)

        # First, check if the user exists
        db_user = self.find_by_username(user.email)
        if not db_user:
            sql = "INSERT OR IGNORE INTO users (name, username, email, job) VALUES (?, ?, ?, ?)"
            args = (user.name, user.username, user.email, user.role)
            with self.dbh.create_cursor() as cursor:
                cursor.execute(sql, args)

            # Now, we can fetch the User
            db_user = self.find_by_username(user.email)
        else:
            progress(f"{db_user.email} already in the DB", indent=2)
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
            username = ?,
            email = ?,
            job = ?
        WHERE
            uid = ?
        """
        args = (user.name, user.username, user.email, user.role, user.uid)
        with self.dbh.create_cursor() as cursor:
            cursor.execute(sql, args)



