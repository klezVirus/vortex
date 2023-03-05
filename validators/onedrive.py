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

from utils.utils import extract_domain, is_subdomain, error
from validators.validator import Validator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Enumerates valid email addresses from Office 365 without submitting login attempts.')
    parser.add_argument('-e', '--email', help='Single email address to validate.')
    parser.add_argument('-f', '--file', help='List of email addresses to validate, one per line.')
    parser.add_argument('-o', '--output', help='Output valid email addresses to the specified file.')
    args = parser.parse_args()


class Onedrive(Validator):
    def __init__(self):
        super().__init__()
        self.__tenant_names = []
        self.__target_credential_type = "https://login.microsoftonline.com/common/GetCredentialType"
        self.__target_sharepoint = 'https://{}-my.sharepoint.com/personal/{}/_layouts/15/onedrive.aspx'
        self.session.headers["Accept"] = "application/json"

    def setup(self, **kwargs):
        self.__tenant_names = kwargs.get("domain", {}).get("Microsoft", {}).get("MS-Tenants", [])
        if len(self.__tenant_names) == 0:
            error("No Microsoft tenant names found.")
            return
        if kwargs.get("aws"):
            self.setup_awsm(self.target, **kwargs)

    def execute(self, email) -> tuple:
        for tenant in self.__tenant_names:
            if self.validate(tenant, email):
                return True, email
        return False, email

    def validate(self, tenant, email):
        url = self.__target_sharepoint.format(tenant, email)
        res = self.session.get(url)
        return res.status_code in [200, 401, 403, 302]


