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
from typing import Union

import requests
import re
import time

from db.enums.errors import IfExistsResult
from utils.utils import res_to_json
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
        self.urls = ["https://outlook.office365.com"]
        self.session.headers["Accept"] = "application/json"

    def execute(self, email) -> tuple:
        result = False
        try:
            res = self.session.get(self.target + f"/autodiscover/autodiscover.json/v1.0/{email}?Protocol=rest")
            if res.status_code == 200:
                json_res = res_to_json(res)
                for k, v in json_res.items():
                    if k.lower() == "url":
                        if v.find("outlook.office.com") > -1:
                            result = True
        except requests.exceptions.TooManyRedirects:
            result = True
        return result, email

