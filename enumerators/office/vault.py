import os
import random
import uuid

from db.enums.errors import AadError
from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, success, debug, extract_domain, extract_main_domain, \
    is_subdomain, error, res_to_json


class VaultEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        # alternate client_id taken from Optiv's Go365
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

    def login(self, username, password) -> tuple:
        client_id = random.choice(self.client_ids)
        data = {
            'resource': 'https://vault.azure.net',
            'client_id': client_id,
            'client_info': '1',
            'grant_type': 'password',
            'username': username,
            'password': password,
            'scope': 'openid',
        }
        url = ""
        res = self.session.post(f"{url}/common/oauth2/token", data=data)

        if res.status_code == 200:
            return True, res
        else:

            json_res = res_to_json(res)
            if not json_res or "error" not in json_res.keys():
                return False, res

            label = json_res.get("error_description")
            err = AadError.from_str(label)

            if err in [AadError.MFA_NEEDED, AadError.EXPIRED_PASSWORD, AadError.LOCKED]:
                error(f"ERROR: Valid user/creds, but no login {username} {err.name}")
                return True, res
            else:
                return False, res
