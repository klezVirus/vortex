import configparser
import traceback
from abc import ABC, abstractmethod
from pydoc import locate

import requests

from utils.utils import get_project_root


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
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(str(get_project_root().joinpath("config", "config.ini")))
        if int(self.config.get("NETWORK", "enabled")) != 0:
            proxy = self.config.get("NETWORK", "proxy")
            self.toggle_proxy(proxy=proxy)

        self.session.max_redirects = 5
        self.debug = int(self.config.get("DEBUG", "developer")) > 0

    def toggle_proxy(self, proxy=None):
        if self.session.proxies is not None and proxy is None:
            self.session.proxies = None
        else:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
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
