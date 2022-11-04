import base64
import os
from threading import Thread

import requests

from enumerators.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import time_label, logfile, get_project_root, warning, debug, error


class CiscoEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.target = target.strip()
        self.group = None
        self.select_group(group=group)
        self.passed = False

    def setup(self, **kwargs):
        pass

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data", "log").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def validate(self) -> tuple:
        url = f"https://{self.target}/+CSCOE+/logon.html"
        res = self.session.get(url, timeout=5)
        soup = BeautifulSoup(res.text, features="html.parser")
        element = soup.find("form", {"id": "unicorn_form"})
        return res.status_code == 200 and (
                res.url.startswith(url) or
                res.url.startswith(url.replace(":443", ""))
            ) and element is not None, res

    def find_groups(self):
        url = f"https://{self.target}/+CSCOE+/logon.html"
        res = self.session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
        soup = BeautifulSoup(res.text, features="html.parser")
        options = soup.find_all("option")
        if len(options) == 0:
            error("No available VPN groups")
            return
        return [o["value"] for o in options]

    def select_group(self, group):
        if group:
            self.group = group
        else:
            groups = self.find_groups()
            print("[*] Select a VPN group:")
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

    def validate_group(self):
        url = f"https://{self.target}/+CSCOE+/logon.html"
        cookies = {
            "webvpnlogin": "1",
            "webvpnLang": "en",
            "tg": f"1{base64.b64encode(self.group.encode()).decode()}"
        }
        res = requests.get(
            url=url,
            cookies=cookies,
            verify=False,
            proxies=self.session.proxies,
            headers=self.session.headers,
            allow_redirects=False
        )
        if res.status_code == 302 and "Location" in res.headers.keys() and res.headers["Location"].find("reason=") > -1:
            url = f"https://{self.target}" + res.headers["Location"]
            res = self.session.get(url)
        else:
            return False
        soup = BeautifulSoup(res.text, features="html.parser")
        input_elements = soup.find_all("input", {"autocomplete": "off"})
        passed = True
        if len(input_elements) != 2:
            passed = False
        if len(input_elements) == 0:
            warning(f"It seems the site is using SSO or a similar mechanism, check the page manually at:")
            debug(url)
        if len(input_elements) == 1:
            warning(f"The site is using an unknown mechanism to login users, check the page manually at:")
            debug(url)
        if len(input_elements) > 2:
            warning(f"It seems the site is using MFA or other mechanism, the tool identified {len(input_elements)} "
                    f"input parameters for the login")
            for element in input_elements:
                print(f"- {element['name']}")
            warning(f"Check the page manually at:")
            debug(url)
        while not passed:
            try:
                input("Press a button to continue or ctrl-c to break...")
                passed = True
                self.passed = True
            except KeyboardInterrupt:
                exit(1)

    def login(self, username, password) -> tuple:
        if not self.passed:
            self.validate_group()
        url = f"https://{self.target}/+webvpn+/index.html"

        self.session.headers["Origin"] = f"https://{self.target}"
        self.session.headers["Referer"] = f"https://{self.target}/+CSCOE+/logon.html"

        data = {
            "tgroup": '',
            "next": '',
            "tgcookieset": '',
            "group_list": self.group,
            "username": username,
            "password": password,
            "Login": "Login"
        }

        res = self.session.post(url, data=data)
        if 400 > res.status_code > 300:
            # Redirect, potential success
            return True, res
        elif res.status_code >= 400:
            # Error
            return False, res
        soup = BeautifulSoup(res.text, features="html.parser")
        script = soup.find('script')
        if not script:
            # We don't have a script nor a redirect? Error
            return False, res
        else:
            # We do have a script
            # It's redirecting to logon page? Failure
            # It's not redirecting to the logon page? It might be a success!
            return script.text.find("logon.html") < 0, res
