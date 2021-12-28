import traceback
from abc import ABC, abstractmethod
from pydoc import locate

import requests


class Validator(ABC):
    def __init__(self):
        self.session = requests.session()
        self.session.verify = False
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Te": "trailers",
            "Connection": "close"
        }

    @abstractmethod
    def execute(self, **kwargs):
        pass

    @staticmethod
    def from_name(name: str):
        try:
            validator_class_string = f"validators.validator.{name.capitalize()}"
            validator_class = locate(validator_class_string)
            return validator_class
        except:
            traceback.print_exc()
            pass
