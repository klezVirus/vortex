import os

import requests

from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.utils import time_label, logfile, get_project_root, info


class CitrixlegacyEnumerator(VpnEnumerator):
    def __init__(self, target, group="dummy"):
        super().__init__()
        self.target = target.strip()
        self.select_group(group)

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        url = f"https://{self.target}/vpn/index.html"
        res = self.session.get(url, timeout=5)
        soup = BeautifulSoup(res.text, features="html.parser")
        element = soup.find("form", {"name": "vpnForm"})
        # Legacy version of Citrix Identified
        return res.status_code == 200 and (
                res.url.startswith(url) or
                res.url.startswith(url.replace(":443", ""))
        ) and element is not None

    def find_groups(self):
        url = f"https://{self.target}/vpn/index.html"
        res = self.session.get(url)
        if res.status_code != 200:
            print(f"[-] {self.__class__.__name__}: Failed to enumerate groups")
            return
        soup = BeautifulSoup(res.text, features="html.parser")
        options = soup.find_all("option")
        if len(options) == 0:
            print("[-] No available VPN groups")
            exit(1)
        return [o["value"] for o in options]

    def select_group(self, group=None):
        if group is not None:
            self.group = group
            return
        groups = self.find_groups()
        info("Select a VPN group:")
        choice = -1

        for n, g in enumerate(groups, start=0):
            print(f"{n} : {g}")
        while choice < 0 or choice > len(groups) - 1:
            try:
                choice = int(input("  $> "))
            except KeyboardInterrupt:
                exit(1)
            except ValueError:
                pass
        self.group = groups[choice]

    def login(self, username, password) -> bool:
        url = f"https://{self.target}/cgi/login"
        cookies = {
            "NSC_TASS": "/robots.txt"
        }
        data = {"login": username,
                "dummy_username": '',
                "dummy_pass1": '',
                "passwd": password
                }

        headers = self.__headers
        headers["Origin"] = f"https://{self.target}"
        headers["Referer"] = f"https://{self.target}/vpn/index.html"

        res = self.session.post(url, headers=headers, cookies=cookies, data=data)
        if res.status_code == 302:
            if "Location" in res.headers.keys():
                if res.headers["Location"].endswith("/vpn/index.html") and len(res.content) == 604:
                    return False
                else:
                    return True
        else:
            return False
