import os
import re

import requests

from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.utils import time_label, logfile, get_project_root, error, info


class SonicwallEnumerator(VpnEnumerator):
    def __init__(self, target, group="dummy"):
        super().__init__()
        self.target = target.strip()
        self.dssignin = "url_default"
        self.__auth_url = None
        self.set_auth_url()
        self.select_group(group)

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        res = self.set_auth_url()
        if len(res.history) == 0:
            return False
        locations = []
        for r in res.history:
            location = r.headers.get("Location")
            if not location:
                continue
            locations.append(location)
        return any([location.find("__extraweb__") >= 0 for location in locations])

    def set_auth_url(self):
        url = f"https://{self.target}"
        res = self.session.get(url, timeout=5)
        self.__auth_url = res.url
        return res

    def find_groups(self):
        url = f"https://{self.target}/dana-na/auth/{self.dssignin}/welcome.cgi"
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

    def select_group(self, group):
        if group:
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
        url = self.__auth_url

        res = self.session.get(url)
        soup = BeautifulSoup(res.text, features="html.parser")

        data = {
            "data_0": username,
            "data_1": password,
            "id": soup.find("input", {"name": "id"}),
            "alias": soup.find("input", {"name": "alias"}),
            "resource": soup.find("input", {"name": "resource"}),
            "method": soup.find("input", {"name": "method"}),
            "nodeID": soup.find("input", {"name": "nodID"})
        }

        headers = self.__headers
        headers["Origin"] = f"https://{self.target}"
        headers["Referer"] = self.__auth_url

        res = self.session.post(url, headers=headers, data=data)
        soup = BeautifulSoup(res.text, features="html.parser")
        element = soup.find("span", {"class": "bodytext error"})

        return element is None

        # Probably too restrictive
        # Needs more testing against SonicWall endpoints
        # if element and element.strip() == "The credentials provided were invalid.":
