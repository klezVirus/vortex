import os

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, error


class FortinetEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]

    def login(self, username, password, **kwargs) -> tuple:
        group = kwargs.get("group")
        url = f"{self.target}/remote/logincheck"

        self.session.headers["Origin"] = f"{self.target}"
        self.session.headers["Referer"] = f"{self.target}/remote/login"

        data = {
            "ajax": "1",
            "username": username,
            "realm": group,
            "credential": password
        }

        res = self.session.post(url, data=data)
        # Failure return something like this:
        # ret=0,redir=/remote/login?&err=sslvpn_login_permission_denied&lang=en
        # If we don't find it, we might have a success
        return res.content.find("redir=/remote/login") == -1, res, username, password, group
