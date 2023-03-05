import os
import re

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, error, info


class WatchguardEnumerator(VpnEnumerator):
    def __init__(self, target, group="dummy"):
        super().__init__()
        self.urls = [f"{target.strip()}"]

    def login(self, username, password, **kwargs) -> tuple:
        group = kwargs.get("group", None)

        data = {
            "fw_username": username,
            "fw_password": password,
            "fw_domain": group,
            "submit": "Login",
            "action": "sslvpn_web_logon",
            "fw_logon_type": "logon",
            "lang": "en-US"
        }

        url = self.target + "/wgcgi.cgi"
        res = self.session.post(url, data=data)
        return "errorcode" not in res.url, res, username, password, group
