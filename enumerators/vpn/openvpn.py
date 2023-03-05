import os

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root


class OpenvpnEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]

    def login(self, username, password, **kwargs) -> tuple:
        group = kwargs.get("group")
        url = f"{self.target}/__auth__"

        self.session.headers["Origin"] = f"{self.target}"
        self.session.headers["Referer"] = f"{self.target}"
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
            return False, res, username, password, group
        else:
            return True, res, username, password, group
