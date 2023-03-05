import os
import random
import uuid

from requests_ntlm import HttpNtlmAuth

from db.enums.errors import AadError
from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, success, debug, extract_domain, extract_main_domain, \
    is_subdomain, error, info, res_to_json


class OktaEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        self.session.headers["Content-Type"] = "application/json"

    def login(self, username, password) -> tuple:
        data = {
            "username": username,
            "password": password,
            "options": {
                "warnBeforePasswordExpired": True,
                "multiOptionalFactorEnroll": True
            }
        }
        res = self.session.post(f"{self.target}/api/v1/authn/", json=data)
        status = "UNKNOWN"
        if res.status_code == 200:
            json_res = res_to_json(res)
            if json_res:
                status = json_res.get("status")
            if status == "SUCCESS":
                # Valid creds
                return True, res
            elif status in ["LOCKED_OUT", "PASSWORD_EXPIRED", "PASSWORD_WARN", "MFA_ENROLL", "MFA_REQUIRED"]:
                # Potentially Valid creds
                return True, res
            else:
                # Potentially Invalid creds
                return False, res
        elif res.status_code in [401, 403]:
            # Potentially Invalid creds or network based rejection
            return False, res
        else:
            # Dunno
            return False, res
