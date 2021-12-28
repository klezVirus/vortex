from db.models.model import Model


class Leak(Model):
    def __init__(self, leak_id, password, uid: int):
        super().__init__()
        self.leak_id = leak_id
        self.password = password
        self.uid = uid

    def to_string(self):
        return f"{self.__class__.__name__} -> {self.uid}:{self.password}"
