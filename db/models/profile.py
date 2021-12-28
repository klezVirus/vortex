from db.models.model import Model


class Profile(Model):
    def __init__(self, pid, url, ptype, user: int):
        super().__init__()
        self.id = pid
        self.url = url
        self.ptype = ptype
        self.user = user

    def to_string(self):
        return f"{self.__class__.__name__} -> {self.url}"
