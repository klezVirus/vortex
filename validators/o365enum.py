#!/usr/bin/python
from typing import Union

# Created by Korey McKinley, Senior Security Consulant at LMG Security
# https://lmgsecurity.com

# July 12, 2019

# This tool will query the Microsoft Office 365 web server to determine
# if an email account is valid or not. It does not need a password and
# should not show up in the logs of a client's O365 tenant.

# Note: Microsoft has implemented some throttling on this service, so
# quick, repeated attempts to validate the same username over and over
# may produce false positives. This tool is best ran after you've gathered
# as many email addresses as possible through OSINT in a list with the
# -f argument.
import argparse
import json

import requests
import re
import time

from bs4 import BeautifulSoup

from db.enums.errors import IfExistsResult
from utils.utils import random_ascii_string, res_to_json
from validators.validator import Validator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enumerates valid email addresses from Office 365 without submitting login attempts.')
    parser.add_argument('-e', '--email', help='Single email address to validate.')
    parser.add_argument('-f', '--file', help='List of email addresses to validate, one per line.')
    parser.add_argument('-o', '--output', help='Output valid email addresses to the specified file.')
    args = parser.parse_args()


class O365Enum(Validator):
    def __init__(self):
        super().__init__()
        self.urls = ["https://login.microsoftonline.com"]

    def execute(self, email) -> tuple:
        r"""
        # The first thing to get is the appId
        res = self.session.get(self.target + "")
        soup = BeautifulSoup(res.text, features="html.parser")
        me_control = soup.find("div", {"id": "meControl"})
        if not me_control:
            return False
        data_sign_in_settings = me_control["data-signinsettings"]
        settings = json.loads(data_sign_in_settings)
        app_id = settings["appId"]
        res = self.session.get(self.target_url)
        soup = BeautifulSoup(res.text, features="html.parser")
        
        # There is a script with a JSON config containing the configuration data
        script = soup.find("script").text
        a = script.find("{")
        b = script.rfind(";")
        data = json.loads(script[a:b])

        s_ctx = data["sCtx"]

        self.session.headers["Origin"] = "https://login.microsoftonline.com"
        self.session.headers["Accept"] = "application/json"
        self.session.headers["hpgact"] = data["hpgact"]
        self.session.headers["hpgid"] = data["hpgid"]
        self.session.headers["client-request-id"] = app_id
        self.session.headers["hpgrequestid"] = res.headers["x-ms-request-id"]
        self.session.headers["Referer"] = res.url
        self.session.headers["Canary"] = random_ascii_string(size=248)

        data = {
            "IsOtherIdpSupported": True,
            "IsRemoteNGCSupported": True,
            "IsAccessPassSupported": True,
            "CheckPhones": False,
            "IsCookieBannerShown": False,
            "IsFidoSupported": False,
            "Forceotclogin": False,
            "IsExternalFederationDisallowed": False,
            "IsRemoteConnectSupported": False,
            "IsSignup": False,
            "FederationFlags": 0,
            "OriginalRequest": s_ctx,
            "Username": email
        }
        """
        result = False
        data = {"Username": email}
        res = self.session.post(self.target + "/common/GetCredentialType", json=data)
        throttle_detected = False
        if res.status_code == 200:
            json_res = res_to_json(res)
            for k, v in json_res.items():
                if k == "IfExistsResult":
                    result = O365Enum.parse_result(v)
                if k == "ThrottleStatus":
                    throttle_detected = (v != 0)

        # We couldn't verify it, returning false
        if result:
            if result == IfExistsResult.THROTTLE or throttle_detected:
                return False, email
            elif result in [IfExistsResult.VALID_USERNAME, IfExistsResult.VALID_USERNAME_2, IfExistsResult.VALID_USERNAME_DIFFERENT_IDP]:
                return True, email

        credential_type = res.json()
        return credential_type["IfExistsResult"] in [0, 6], email

    @staticmethod
    def parse_result(result: Union[int, str]) -> IfExistsResult:
        if isinstance(result, str):
            try:
                result = int(result)
            except ValueError:
                return IfExistsResult.UNKNOWN_ERROR
        return IfExistsResult.from_value(result)