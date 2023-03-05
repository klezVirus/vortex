from db.models.model import Model


class Login(Model):
    def __init__(self, login_id, realm, group, email, password, eid):
        super().__init__()
        self.login_id = login_id
        self.realm = realm
        self.group = group
        self.email = email
        self.password = password
        self.eid = eid

    def to_string(self):
        return f"{self.__class__.__name__} -> {self.email}:{self.password} at {self.eid} on {self.realm} and {self.group}"

