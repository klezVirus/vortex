import json

from db.models.model import Model


class Endpoint(Model):
    def __init__(self, eid, target, email_format, etype_ref: int, additional_info=None):
        super().__init__()
        self.eid = eid
        self.target = target
        self.email_format = email_format
        self.etype_ref = etype_ref
        self.__additional_info = None
        if isinstance(additional_info, str):
            self.additional_info_str = additional_info
        elif isinstance(additional_info, dict):
            self.additional_info_json = additional_info
        else:
            self.additional_info_json = {"raw": additional_info}

    @property
    def additional_info_json(self):
        return self.__additional_info

    @additional_info_json.setter
    def additional_info_json(self, value: dict):
        self.__additional_info = value if value else {}

    @property
    def additional_info_str(self):
        return json.dumps(self.__additional_info)

    @additional_info_str.setter
    def additional_info_str(self, value: str):
        self.__additional_info = json.loads(value) if value else {}

    @property
    def domain(self):
        tokens = self.target.split(".")
        if tokens[-2] == "co":
            domain = ".".join(tokens[-3:])
        else:
            domain = ".".join(tokens[-2:])
        return domain

    def to_string(self):
        return f"{self.__class__.__name__}: \n" \
               f"\t Target -> {self.target}\n" \
               f"\t Endpoint Type Id -> {self.etype_ref}\n" \
               f"\t Email FMT -> {self.email_format}\n" \
               f"\t INFO -> {self.additional_info_str}\n"



