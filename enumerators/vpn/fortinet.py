import os
import re

import requests

from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.utils import time_label, logfile, get_project_root, error


class FortinetEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.target = target.strip()
        self.realm = ""
        self.group = ""
        self.select_group(group=group)

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        url = f"https://{self.target}/remote/login"
        res = self.session.get(url, timeout=5)
        history = [r for r in res.history if r.status_code == 302]
        if len(history) > 0 and res.status_code == 200:
            for elem in history:
                for header, value in elem.headers.items():
                    if header.lower() != "location":
                        continue
                    if value.find("lang=") > -1:
                        return True
        return False

    def find_groups(self):
        url = f"https://{self.target}/remote/login"
        res = self.session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
        soup = BeautifulSoup(res.text, features="html.parser")
        self.realm = soup.find("input", {"name": "realm"})
        self.group = soup.find("input", {"name": "grpid"})

    def select_group(self, group):
        if group:
            self.group = group
        else:
            self.find_groups()

    def login(self, username, password) -> tuple:
        url = f"https://{self.target}/remote/logincheck"

        self.session.headers["Origin"] = f"https://{self.target}"
        self.session.headers["Referer"] = f"https://{self.target}/remote/login"

        data = {
            "ajax": "1",
            "username": username,
            "realm": self.realm,
            "credential": password
        }

        res = self.session.post(url, data=data)
        # Failure return something like this:
        # ret=0,redir=/remote/login?&err=sslvpn_login_permission_denied&lang=en
        # If we don't find it, we might have a success
        return res.content.find("redir=/remote/login") == -1, str(res.status_code), len(res.content)
