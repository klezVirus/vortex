import os

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, error


class F5Enumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        self.group = None
        self.select_group(group=group)

    def find_groups(self):
        url = f"{self.target}/my.policy"
        res = self.session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
        soup = BeautifulSoup(res.text, features="html.parser")
        return soup.find("input", {"name": "vhost"})

    def select_group(self, group):
        if group:
            self.group = group
        else:
            group = self.find_groups()
            if group:
                self.group = group["value"]

    def login(self, username, password, **kwargs) -> tuple:
        group = kwargs.get("group")
        url = f"{self.target}/my.policy"

        self.session.headers["Origin"] = f"{self.target}"
        self.session.headers["Referer"] = f"{self.target}/my.policy"

        data = {
            "username": "test",
            "password": "test",
            "vhost": group
        }

        res = self.session.post(url, data=data)
        return res.text.find("The username or password is not correct.") < 0, res, username, password, group
