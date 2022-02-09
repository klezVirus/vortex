import os

import requests
from colorama import Fore
from requests_ntlm import HttpNtlmAuth

from enumerators.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.ntlmdecoder import ntlmdecode
from utils.utils import time_label, logfile, get_project_root, colors, error, warning, debug


# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r

class OwaEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        if self.debug:
            debug(f"{self.__class__.__name__}: Initializing")
        self.target = target
        self.autodiscover_url = None
        self.netbios_domain = None
        self.internally_hosted = False
        if not self.find_autodiscover_url() and self.debug:
            debug(f"{self.__class__.__name__}: Couldn't detect autodiscover URL", indent=2)
        if not self.find_owa_domain() and self.debug:
            debug(f"{self.__class__.__name__}: Couldn't detect OWA domain", indent=2)

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def validate(self) -> bool:
        domain = self.target.split(":")[0]
        url = f"https://login.microsoftonline.com/{domain}/.well-known/openid-configuration"
        r = self.session.get(url)
        if r.status_code == 400:
            warning("OWA domain appears to be hosted internally")
            return True
        elif r.status_code == 200:
            return True
        return False

    def find_autodiscover_url(self):
        domain = self.target.split(":")[0]
        urls = [
            f"https://autodiscover.{domain}/autodiscover/autodiscover.xml",
            f"http://autodiscover.{domain}/autodiscover/autodiscover.xml",
            f"https://{domain}/autodiscover/autodiscover.xml",
        ]

        headers = {"Content-Type": "text/xml"}
        for url in urls:
            try:
                r = requests.get(url, headers=headers, verify=False)
                if r.status_code == 401 or r.status_code == 403:
                    self.autodiscover_url = url
                    return True
            except ConnectionError:
                continue
            except:
                continue
        return False

    def find_owa_domain(self):
        ntlm_info = {
            "NetBIOS_Domain_Name": None
        }
        auth_header = {"Authorization": "NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw=="}
        try:
            r = requests.post(self.autodiscover_url, headers=auth_header, verify=False)
            if r.status_code == 401:
                ntlm_info = ntlmdecode(r.headers["WWW-Authenticate"])

            self.netbios_domain = ntlm_info["NetBIOS_Domain_Name"]
        except:
            pass
        return self.netbios_domain is not None

    def login(self, username, password) -> tuple:
        if not self.autodiscover_url:
            url = "https://autodiscover-s.outlook.com/autodiscover/autodiscover.xml"
            auth = (username, password)
            valid_auth_codes = [200, 456]
        else:
            url = self.autodiscover_url
            auth = HttpNtlmAuth(username, password)
            valid_auth_codes = [200]

        self.session.headers["Content-Type"] = "text/xml"
        res = self.session.get(url, auth=auth)
        return res.status_code in valid_auth_codes, str(res.status_code), len(res.content)
