import os

import requests
import requests_html

from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.utils import *


class CitrixlegacyEnumerator(VpnEnumerator):
    def __init__(self, target, group="dummy"):
        super().__init__()
        self.html_session = requests_html.HTMLSession()
        self.html_session.headers = self.session.headers
        self.html_session.proxies = self.session.proxies
        self.html_session.verify = self.session.verify
        self.target = target.strip()
        self.group_field = None
        self.skip_group = False
        self.select_group(group)

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        url = f"https://{self.target}/vpn/index.html"
        res = self.session.get(url)
        soup = BeautifulSoup(res.text, features="html.parser")
        e1 = soup.find("form", {"name": "vpnForm"})

        e2 = [a["href"] for a in soup.find_all("link") if hasattr(a, "href") and a["href"].find("citrix") > -1]
        e3 = soup.find("title").text if soup.find("title") else None
        # Legacy version of Citrix Identified
        if not(res.status_code == 200 and (
                res.url.startswith(url) or
                res.url.startswith(url.replace(":443", ""))
        )):
            return False

        return e1 is not None or e2 or e3.lower().find("citrix") > -1 or e3.lower().find("gateway") > -1

    def find_groups(self):
        groups = []
        path = "/vpn/index.html"
        url = f"https://{self.target}{path}"
        res = self.html_session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
        soup = BeautifulSoup(res.text, features="html.parser")
        select = soup.find("select")
        if select and hasattr(select, "name"):
            self.group_field = select["name"]
        options = soup.find_all("option")
        if len(options) > 0:
            groups = [o["value"] for o in options]
        else:
            warning("Couldn't identify the group selection box")
            info("Do you want to skip the group selection and proceed without an groups?")
            choice = "k"
            while choice.lower().strip() not in ["y", "n"]:
                choice = input("  [y|n] $> ")
            if choice == "y":
                self.skip_group = True

            if not self.skip_group:
                info("Do you want to override the target path?")
                progress(f"Current path: {path}", indent=2)



                path = input("  $> ")
                if not path.strip().startswith("/"):
                    warning("Invalid path")

                info("Loading via JavaScript...")
                url = f"https://{self.target}{path}"
                res = self.html_session.get(url)
                res.html.render()
                soup = BeautifulSoup(res.html.html, features="html.parser")
                select = soup.find("select")
                if select and hasattr(select, "name"):
                    self.group_field = select["name"]
                options = soup.find_all("option")
                if len(options) > 0:
                    groups = [o["value"] for o in options]
        # for key, value in res.cookies.items():
        #         if (
        #             key.lower().find("domains") > -1 or
        #             key.lower().find("groups") > -1
        #             ) and len(value.split(",")) > 0:
        #         progress(f"Found potential group list: {value}", indent=2)
        #         groups = [g.strip() for g in value.split(",")]
        #    elif key.lower().find("domain") > -1 or key.lower().find("group") > -1:
        #         progress(f"Found potential group key: {key}", indent=2)
        #        self.group_field = key
                if len(groups) == 0:
                    error("No available VPN groups")
                    exit(1)
        return groups

    def select_group(self, group=None):
        if group is not None:
            self.group = group
            return
        groups = self.find_groups()
        if self.skip_group:
            self.group = None
            return
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

    def login(self, username, password) -> tuple:
        url = f"https://{self.target}/cgi/login"
        # cookies = {
        #     "NSC_TASS": "/robots.txt"
        # }
        data = {"login": username,
                "dummy_username": '',
                "dummy_pass1": '',
                "passwd": password
                }
        if self.group_field and self.group:
            data[self.group_field] = self.group
        elif self.group:
            warning("Multiple groups identified, but couldn't identify group field", indent=2)
            warning("The group field is the parameter name of the group in the POST request", indent=2)
            info("Please provide a valid group field:", indent=2)
            self.group_field = input("  $> ")
            if not self.group_field:
                error(f"Group field not provided, skipping {username}:{password}", indent=2)
                return False
            else:
                data[self.group_field] = self.group

        headers = self.session.headers
        headers["Origin"] = f"https://{self.target}"
        headers["Referer"] = f"https://{self.target}/vpn/index.html"

        res = requests.post(url, cookies=self.session.cookies, headers=headers, data=data)
        if res.status_code == 302:
            if "Location" in res.headers.keys():
                if res.headers["Location"].endswith("/vpn/index.html") and len(res.content) == 604:
                    return False, str(res.status_code), len(res.content)
                else:
                    return True, str(res.status_code), len(res.content)
        else:
            return False, str(res.status_code), len(res.content)
