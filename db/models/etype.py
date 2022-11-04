from db.models.model import Model


class Etype(Model):
    def __init__(self, etid, name, is_vpn=False, is_office=False, is_o365=False):
        super().__init__()
        self.etid = etid
        self.name = name
        self.is_vpn = is_vpn
        self.is_office = is_office
        self.is_o365 = is_o365

    def to_string(self):
        return f"{self.__class__.__name__} -> " \
               f"{self.name} " \
               f"(VPN={self.is_vpn}:Office={self.is_office}:O365={self.is_o365}:)"


