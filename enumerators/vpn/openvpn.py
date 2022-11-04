import os
import re

import requests

from enumerators.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import time_label, logfile, get_project_root, error


class OpenvpnEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.target = target.strip()

    def setup(self, **kwargs):
        pass

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data", "log").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def validate(self) -> tuple:
        url = f"https://{self.target}/?src=connect"
        res = self.session.get(url, timeout=5)
        history = [r for r in res.history if r.status_code == 302]
        soup = BeautifulSoup(res.text, features="html.parser")
        element = soup.find("div", {"id": "cws-card"})
        return res.text.find("openvpn") > -1 and element, res

    def login(self, username, password) -> tuple:
        url = f"https://{self.target}/__auth__"

        self.session.headers["Origin"] = f"https://{self.target}"
        self.session.headers["Referer"] = f"https://{self.target}"
        self.session.headers["X-Openvpn"] = "1"
        self.session.headers["X-Cws-Proto-Ver"] = "2"

        data = {
            "username": username,
            "password": password
        }

        if not any([v for k, v in self.session.cookies.get_dict().items() if v.startswith("openvpn")]):
            res = self.session.post(url, data=data)
        res = self.session.post(url, data=data)

        if res.status_code >= 400 or res.text.find("failure") > -1:
            return False, res
        else:
            return True, res
