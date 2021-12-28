import os

import requests
from imapclient import imapclient
from requests_ntlm import HttpNtlmAuth

from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.ntlmdecoder import ntlmdecode
from utils.utils import time_label, logfile, get_project_root


# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/imap.py
# CREDIT: @byt3bl33d3r

class ImapEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.target = target

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        if self.target.find(":") > -1:
            host, port = self.target.split(":")
        else:
            host, port = self.target, 993
        try:
            server = imapclient.IMAPClient(self.target, port=port, ssl=True, timeout=3)
            server.login("IWouldNeverExistOnThisServer", "IWouldNeverBeAValidPassword")
        except Exception as e:
            return e == imapclient.exceptions.LoginError

    def login(self, username, password) -> bool:
        host, port = self.target.split(":")
        if not port:
            port = 993
        try:
            server = imapclient.IMAPClient(self.target, port=port, ssl=True, timeout=3)
            server.login(username, password)
            return True
        except imapclient.exceptions.LoginError:
            return False
        except Exception as e:
            pass