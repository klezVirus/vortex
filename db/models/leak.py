from db.models.model import Model


class Leak(Model):
    def __init__(self, leak_id: int, uid: int, password, hashed, address, phone, database: str):
        super().__init__()
        self.leak_id = leak_id
        self.uid = uid
        self.password = password
        self.hashed = hashed
        self.address = address
        self.phone = phone
        self.database = database

    def to_string(self):
        return f"P:{self.password} H:{self.hashed} Ph:{self.phone} A:{self.address}"
