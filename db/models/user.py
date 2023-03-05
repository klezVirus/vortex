from db.models.model import Model


class User(Model):
    def __init__(self, uid, name, email, role, valid: bool = False):
        super().__init__()
        self.uid = uid
        self.name = name
        self.email = email
        self.role = role
        self.valid = valid
        self.leaks = []
        self.profiles = []

    def update(self, user):
        if self.name in [None, ""]:
            self.name = user.name
        if self.role in [None, ""]:
            self.role = user.role
        if self.valid in [False]:
            self.valid = user.valid
        if len(self.leaks) == 0:
            self.leaks = user.leaks
        if len(self.profiles) == 0:
            self.profiles = user.profiles

    def to_string(self):
        return f"{self.__class__.__name__} -> {self.email}"

    def to_string_ex(self):
        return f"{self.__class__.__name__} -> {self.email}:{','.join(self.leaks)}"

