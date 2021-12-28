from db.models.model import Model


class Endpoint(Model):
    def __init__(self, eid, target, endpoint_type, is_o365=False):
        super().__init__()
        self.eid = eid
        self.target = target
        self.endpoint_type = endpoint_type
        self.is_o365 = is_o365

    def to_string(self):
        return f"{self.__class__.__name__} -> {self.target}"


