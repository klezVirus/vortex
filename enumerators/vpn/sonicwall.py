import os
import re

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, error, info


class SonicwallEnumerator(VpnEnumerator):
    def __init__(self, target, group="dummy"):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        self.dssignin = "url_default"
        self.__auth_url = None
        self.__groups = None
        if group != "dummy":
            self.set_auth_url()
            self.select_group(group)

    def set_auth_url(self):
        url = f"{self.target}"
        res = self.session.get(url, timeout=5)
        self.__auth_url = res.url
        return res

    def find_groups(self):
        url = f"{self.target}/sslvpnLogin.html"
        res = self.session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
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

    def login(self, username, password, **kwargs) -> tuple:
        group = kwargs.get("group", "N/A")
        url = self.__auth_url

        res = self.session.get(url)
        soup = BeautifulSoup(res.text, features="html.parser")

        data = {
            "data_0": username,
            "data_1": password,
            "id": soup.find("input", {"name": "id"}).get("value") if soup.find("input", {"name": "id"}) else "",
            "alias": soup.find("input", {"name": "alias"}).get("value") if soup.find("input", {"name": "alias"}) else "",
            "resource": soup.find("input", {"name": "resource"}).get("value") if soup.find("input", {"name": "resource"}) else "",
            "method": soup.find("input", {"name": "method"}).get("value") if soup.find("input", {"name": "method"}) else "",
            "nodeID": soup.find("input", {"name": "nodID"}).get("value") if soup.find("input", {"name": "nodeID"}) else ""
        }

        headers = self.__headers
        headers["Origin"] = f"{self.target}"
        headers["Referer"] = self.__auth_url

        res = self.session.post(url, headers=headers, data=data)
        soup = BeautifulSoup(res.text, features="html.parser")
        element = soup.find("span", {"class": "bodytext error"})

        return element is None, res, username, password, group

        # Probably too restrictive
        # Needs more testing against SonicWall endpoints
        # if element and element.strip() == "The credentials provided were invalid.":
