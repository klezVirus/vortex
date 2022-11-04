import json

import tldextract.tldextract

from db.models.model import Model


class Domain(Model):
    def __init__(self, did, name, email_format, additional_info=None, level=None):
        super().__init__()
        self.did = did
        self.name = name
        self.level = 2
        if level:
            self.level = level
        else:
            ext = tldextract.tldextract.extract(name)
            if ext.subdomain != "":
                self.level = 3
        self.email_format = email_format
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

    def to_string(self):
        return f"{self.__class__.__name__}: \n" \
               f"\t Name -> {self.name}\n" \
               f"\t Level -> {self.level}\n" \
               f"\t Email FMT -> {self.email_format}\n" \
               f"\t INFO -> {self.additional_info_str}\n"


