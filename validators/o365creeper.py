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

import requests
import re
import time

from validators.validator import Validator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enumerates valid email addresses from Office 365 without submitting login attempts.')
    parser.add_argument('-e', '--email', help='Single email address to validate.')
    parser.add_argument('-f', '--file', help='List of email addresses to validate, one per line.')
    parser.add_argument('-o', '--output', help='Output valid email addresses to the specified file.')
    args = parser.parse_args()


class O365Creeper(Validator):
    def __init__(self):
        super().__init__()
        self.__target_credential_type = "https://login.microsoftonline.com/common/GetCredentialType"
        self.__target_autodiscover = "https://outlook.office365.com/autodiscover/autodiscover.json/v1.0/{}?Protocol=rest"
        self.session.headers["Accept"] = "application/json"

    def execute(self, **kwargs):
        email = ""
        if "email" not in kwargs.keys() and ("domain" not in kwargs.keys() or "user" not in kwargs.keys()):
            return False
        if "email" in kwargs.keys():
            email = kwargs["email"]
        elif "domain" in kwargs.keys() and "username" in kwargs.keys():
            email = kwargs["username"] + "@" + kwargs["domain"]
        result = [False, False]
        # First attempt
        res = self.session.get(self.__target_autodiscover.format(email))
        if res.status_code == 200:
            for k, v in res.json().items():
                if k.lower() == "url":
                    if v.find("outlook.office.com") > -1:
                        result[0] = True
        # Second attempt
        data = {"Username": email}
        res = self.session.post(self.__target_credential_type, json=data)
        if res.status_code == 200:
            for k, v in res.json().items():
                if k == "IfExistsResult":
                    result[1] = (v == 0)
        # We couldn't verify it, returning false
        return all(result)

    def domain_validate(self, **kwargs):
        email = ""
        if "email" not in kwargs.keys() and ("domain" not in kwargs.keys() or "user" not in kwargs.keys()):
            return False
        if "email" in kwargs.keys():
            email = kwargs["email"]
        elif "domain" in kwargs.keys() and "username" in kwargs.keys():
            email = kwargs["username"] + "@" + kwargs["domain"]
        result = [False, False]
        # First attempt
        res = self.session.get(self.__target_autodiscover.format(email))
        if res.status_code == 200:
            for k, v in res.json().items():
                if k.lower() == "url":
                    if v.find("outlook.office.com") > -1:
                        result[0] = True
        # Second attempt
        data = {"Username": email}
        res = self.session.post(self.__target_credential_type, json=data)
        if res.status_code == 200:
            for k, v in res.json().items():
                if k == "IfExistsResult":
                    result[1] = (v == 0)
        # We couldn't verify it, returning false
        return all(result)

