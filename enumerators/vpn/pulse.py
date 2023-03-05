import os
import re

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, error, info


class PulseEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        self.dssignin = "url_default"

        if group:
            self.group = group
        else:
            self.select_group()

    def find_groups(self):
        url = f"{self.target}/dana-na/auth/{self.dssignin}/welcome.cgi"
        res = self.session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
        if len(res.history) > 0:
            if "location" in [h.lower() for h in res.history[-1].headers.keys()]:
                self.dssignin = res.history[-1].headers["Location"].split("/")[3]
        soup = BeautifulSoup(res.text, features="html.parser")
        options = soup.find_all("option")
        if len(options) == 0:
            for inp in soup.find_all("input", {"type": "hidden"}):
                if "id" not in inp.keys():
                    continue
                if re.search(inp["value"], "realm", re.IGNORECASE):
                    return inp["value"]
            error("No available VPN groups")
            return
        return [o["value"] for o in options]

    def login(self, username, password, **kwargs) -> tuple:
        group = kwargs.get("group")
        url = f"{self.target}/dana-na/auth/{self.dssignin}/login.cgi"
        cookies = {
            "lastRealm": group,
            "DSSIGNIN": {self.dssignin},
            "DSSignInURL": "/nc"
        }

        headers = self.__headers
        headers["Origin"] = f"{self.target}"
        headers["Referer"] = f"{self.target}/dana-na/auth/{self.dssignin}/welcome.cgi"

        data = {
            "tz_offset": "0",
            "username": f"{username}",
            "password": f"{password}",
            "realm": self.group,
            "btnSubmit": "Sign In"
        }

        res = self.session.post(url, headers=headers, cookies=cookies, data=data)
        history = [r for r in res.history if r.status_code == 302]
        if len(history) > 0 and res.status_code == 200:
            for elem in history:
                for header, value in elem.headers.items():
                    if header.lower() != "location":
                        continue
                    if value.find("p=failed") > -1:
                        return False, str(res.status_code), len(res.content), username, password, group
            return True, res, username, password, group
        else:
            return False, res, username, password, group
