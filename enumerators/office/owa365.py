import os
import traceback

from requests_ntlm import HttpNtlmAuth

from enumerators.interfaces.enumerator import VpnEnumerator

from utils.ntlmdecoder import ntlmdecode
from utils.utils import *


# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r

class Owa365Enumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"https://outlook.office365.com"]
        self.session.headers["Content-Type"] = "text/xml"

    def validate(self) -> tuple:
        return None, None

    def login(self, username, password) -> tuple:
        url = f"{self.target}/autodiscover/autodiscover.xml"
        valid_auth_codes = [200, 456]
        res = self.session.get(url, auth=(username, password))
        return res.status_code in valid_auth_codes, res
