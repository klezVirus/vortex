import os

import requests_html

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import *


class CitrixlegacyEnumerator(VpnEnumerator):
    def __init__(self, target, group="dummy"):
        super().__init__()
        self.urls = [f"{target.strip()}"]

    def login(self, username, password, **kwargs) -> tuple:
        group = kwargs.get("group")
        url = f"{self.target}/cgi/login"

        data = {"login": username,
                "dummy_username": '',
                "dummy_pass1": '',
                "passwd": password
                }
        if self.group_field and group:
            data[self.group_field] = group
        if not self.group_field:
            error(f"Group field not identified, skipping {username}:{password}")
            return False, None, username, password, group
        else:
            data[self.group_field] = self.group

        headers = self.session.headers
        headers["Origin"] = f"{self.target}"
        headers["Referer"] = f"{self.target}/vpn/index.html"

        res = self.session.post(url, cookies=self.session.cookies, headers=headers, data=data)

        return self.detect_success(res), res, username, password, group

    def detect_success(self, res):
        soup = BeautifulSoup(res.text, features="html.parser")
        return soup.find("form", {"name": "vpnForm"}) is not None

    def old_detect_success(self, res):
        if res.status_code == 302:
            if res.headers.get("Location"):
                if res.headers.get("Location").endswith("/vpn/index.html"):
                    return False
                else:
                    return True
        else:
            return False
