import json

import tldextract.tldextract

from db.models.model import Model


class Domain(Model):
    def __init__(self, did, name, email_format, dns=None, frontable=None, takeover=None, additional_info=None, level=None):
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
        self.__dns = None
        self.__frontable = None
        self.__takeover = None
        self.__additional_info = None
        # INFO
        if isinstance(additional_info, str):
            self.additional_info_str = additional_info
        elif isinstance(additional_info, dict):
            self.additional_info_json = additional_info
        else:
            self.additional_info_json = {"raw": additional_info}
        # TAKEOVER
        if isinstance(takeover, str):
            self.takeover_str = takeover
        elif isinstance(takeover, dict):
            self.takeover_json = takeover
        else:
            self.takeover_json = None
        # DNS
        if isinstance(dns, str):
            self.dns_str = dns
        elif isinstance(dns, dict):
            self.dns_json = dns
        else:
            self.dns_json = {"A": None, "AAAA": None, "CNAME": None, "MX": None, "NS": None, "TXT": None}
        # DOMAIN FRONTING
        if isinstance(frontable, str):
            self.frontable_str = frontable
        elif isinstance(frontable, dict):
            self.frontable_json = frontable
        else:
            self.frontable_json = None

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
    def dns_json(self):
        return self.__dns

    @dns_json.setter
    def dns_json(self, value: dict):
        self.__dns = value if value else {}

    @property
    def dns_str(self):
        return json.dumps(self.__dns)

    @dns_str.setter
    def dns_str(self, value: str):
        self.__dns = json.loads(value) if value else {}

    @property
    def takeover_json(self):
        return self.__takeover

    @takeover_json.setter
    def takeover_json(self, value: dict):
        self.__takeover = value if value else {}

    @property
    def takeover_str(self):
        return json.dumps(self.__takeover)

    @takeover_str.setter
    def takeover_str(self, value: str):
        self.__takeover = json.loads(value) if value else {}

    @property
    def frontable_json(self):
        return self.__frontable

    @frontable_json.setter
    def frontable_json(self, value: dict):
        self.__frontable = value if value else {}

    @property
    def frontable_str(self):
        return json.dumps(self.__frontable)

    @frontable_str.setter
    def frontable_str(self, value: str):
        self.__frontable = json.loads(value) if value else {}

    def to_string(self):
        return f"{self.__class__.__name__}: \n" \
               f"\t Name -> {self.name}\n" \
               f"\t Level -> {self.level}\n" \
               f"\t Email FMT -> {self.email_format}\n" \
               f"\t DNS -> {self.dns_str}\n" \
               f"\t Fronting -> {self.frontable_str}\n" \
               f"\t Takover -> {self.takeover_str}\n" \
               f"\t INFO -> {self.additional_info_str}\n"


