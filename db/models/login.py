from db.models.model import Model


class Login(Model):
    def __init__(self, login_id, email, password, url):
        super().__init__()
        self.login_id = login_id
        self.email = email
        self.password = password
        self.url = url

    def to_string(self):
        return f"{self.__class__.__name__} -> {self.email}:{self.password} at {self.url}"

