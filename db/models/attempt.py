from db.models.model import Model


class Attempt(Model):
    def __init__(self, attempt_id, user_id, etype_ref, realm, group, username, password, url, created_at=None):
        super().__init__()
        self.attempt_id = attempt_id
        self.user_id = user_id
        self.etype_ref = etype_ref
        self.realm = realm
        self.group = group
        self.username = username
        self.password = password
        self.url = url
        self.created_at = created_at

    def to_string(self):
        return f"[{self.__class__.__name__}] ({self.etype_ref}) -> {self.realm} - {self.username}:{self.password} at {self.url}"

