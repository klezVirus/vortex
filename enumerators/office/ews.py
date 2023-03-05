import os
import random
import uuid

from requests_ntlm import HttpNtlmAuth

from db.enums.errors import AadError
from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, success, debug, extract_domain, extract_main_domain, \
    is_subdomain, error, info


class EwsEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        self.session.headers["Content-Type"] = "text/xml; charset=utf-8"

    def login(self, username, password) -> tuple:
        res = self.session.post(f"{self.target}/ews/", auth=HttpNtlmAuth(username, password))

        if res.status_code in [500, 504]:
            info(f"Potentially valid creds: {username}:{password}")
            return True, res
        elif res.status_code == 401:
            return True, res
        else:
            return False, res
