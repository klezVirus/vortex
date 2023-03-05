import json

from db.models.model import Model


class Origin(Model):
    def __init__(self, oid, host, port, ssl: bool = False, up: bool = True):
        super().__init__()
        self.oid = oid
        self.host = host
        self.port = port
        self.ssl = ssl
        self.up = up

    @property
    def origin(self):
        return f"{self.host}:{self.port}"

    @origin.setter
    def origin(self, value):
        self.host, self.port = value.split(":")

    def to_string(self):
        return f"{self.__class__.__name__}: \n" \
               f"\t Address -> {self.host}\n" \
               f"\t Port -> {self.port}\n" \
               f"\t SSL -> {self.ssl}\n" \
               f"\t Open -> {self.up}\n"


