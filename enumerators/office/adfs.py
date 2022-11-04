import os
import uuid

import requests
from requests_ntlm import HttpNtlmAuth

from enumerators.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.ntlmdecoder import ntlmdecode
from utils.utils import time_label, logfile, get_project_root, success, debug, extract_domain, extract_main_domain, \
    is_subdomain


class AdfsEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        if self.debug:
            debug(f"{self.__class__.__name__}: Initializing")
        self.target = target
        self.auth_url = None
        self.user_realm = None
        self.auth_url_response = None

    def setup(self, **kwargs):
        bkp = kwargs.copy()
        di = kwargs.get("Domain")
        if "Microsoft" not in di.keys():
            di["Microsoft"] = {}
        self.user_realm = di.get("Microsoft", {}).get("UserRealm")
        if not self.user_realm:
            r, self.auth_url_response = self.get_user_realm()
        di["Microsoft"]["UserRealm"] = self.user_realm
        bkp["Domain"] = di
        if bkp != kwargs:
            self.additional_info = bkp
            self.has_new_info = True

    def get_user_realm(self) -> tuple:
        if is_subdomain(self.target):
            return False, None

        domain = extract_main_domain(self.target)
        url = f"https://login.microsoftonline.com:443/getuserrealm.srf?login={domain}"
        res = None
        try:
            res = self.session.get(url)
            user_realm = res.json()
            self.user_realm = user_realm
            return True, res
        except:
            return False, res

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def validate(self) -> tuple:
        extract_domain(self.target)
        return self.auth_url is not None, self.auth_url_response

    def get_auth_url(self):
        if self.user_realm.get("NameSpaceType") not in ["Unknown", "Managed"] and "AuthURL" in self.user_realm.keys():
            self.auth_url = self.user_realm.get("AuthURL")

    def login(self, username, password) -> tuple:
        if not self.auth_url:
            return False, None
        form = None
        res = self.session.get(self.auth_url)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, features="html.parser")
            form = soup.find("form", {"id": "loginForm"})
        if not form or not form.has_attr("action"):
            debug("Something went wrong recovering the login URL+uuid", indent=2)
            client_request_id = str(uuid.uuid4())
            url = f"{res.url}&client-request-id={client_request_id}"
        else:
            url = "/".join(res.url.split("/")[:3]) + form["action"]

        data = {
            "UserName": username,
            "Password": password,
            "AuthMethod": "FormsAuthentication"
        }

        res = self.session.post(url, data=data)
        if res.status_code == 302:
            return True, res
        elif res.text.find("Your password has expired") > -1:
            success(f"{username}:{password} is valid but the password has expired", indent=2)
            return True, res
        return False, res
