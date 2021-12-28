#!/usr/bin/python

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

from utils.utils import random_ascii_string
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

    def execute(self, **kwargs):
        email = ""
        if "email" not in kwargs.keys() and ("domain" not in kwargs.keys() or "user" not in kwargs.keys()):
            return False
        if "email" in kwargs.keys():
            email = kwargs["email"]
        elif "domain" in kwargs.keys() and "username" in kwargs.keys():
            email = kwargs["username"] + "@" + kwargs["domain"]
        # The first thing to get is the appId
        url = "https://www.office.com/login?es=Click&ru=/&msafed=0"
        res = self.session.get(url)
        soup = BeautifulSoup(res.text, features="html.parser")
        me_control = soup.find("div", {"id": "meControl"})
        if not me_control:
            return False
        data_sign_in_settings = me_control["data-signinsettings"]
        settings = json.loads(data_sign_in_settings)
        app_id = settings["appId"]

        url = "https://www.office.com/login?es=Click&ru=/&msafed=0"
        res = self.session.get(url)
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

        url = "https://login.microsoftonline.com/common/GetCredentialType?mkt=en-US"
        res = self.session.post(url, json=data)

        credential_type = res.json()
        return credential_type["IfExistsResult"] in [0, 6]

