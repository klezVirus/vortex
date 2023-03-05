import os
from datetime import datetime, timedelta

import requests
import xmltodict

from db.enums.errors import AadError
from enumerators.interfaces.enumerator import VpnEnumerator
import urllib.parse as urlparse

from utils.utils import logfile, get_project_root, SimpleUTC, error, debug, res_to_json


# Disclaimer
# The code for the Lynk enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/lynk.py
# CREDIT: @byt3bl33d3r

class LyncEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]

    def login(self, username, password) -> tuple:
        url = self.target + "/WebTicket/oauthtoken"
        data = {
            "grant_type": "password",
            "username": username,
            "password": password
        }
        res = self.session.post(url, data=data)
        return "access_token" in res.json().keys(), res
