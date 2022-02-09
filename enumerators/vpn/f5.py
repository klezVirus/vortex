import base64
import os
from threading import Thread

import requests

from enumerators.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import time_label, logfile, get_project_root, warning, debug, error


class F5Enumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.target = target.strip()
        self.group = None
        self.select_group(group=group)

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def validate(self) -> bool:
        url = f"https://{self.target}"
        res = self.session.get(url, timeout=5)
        my_policy = any([r.headers.get("Location").find("my.policy") > -1 for r in res.history if r.headers.get("Location")])
        return res.status_code == 200 and my_policy

    def find_groups(self):
        url = f"https://{self.target}/my.policy"
        res = self.session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
        soup = BeautifulSoup(res.text, features="html.parser")
        return soup.find("input", {"name": "vhost"})

    def select_group(self, group):
        if group:
            self.group = group
        else:
            group = self.find_groups()
            if group:
                self.group = group["value"]

    def login(self, username, password) -> tuple:
        url = f"https://{self.target}/my.policy"

        self.session.headers["Origin"] = f"https://{self.target}"
        self.session.headers["Referer"] = f"https://{self.target}/my.policy"

        data = {
            "username": "test",
            "password": "test",
            "vhost": self.group
        }

        res = self.session.post(url, data=data)
        return res.text.find("The username or password is not correct.") < 0, res
