import os

import requests
from imapclient import imapclient
from requests_ntlm import HttpNtlmAuth

from enumerators.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.ntlmdecoder import ntlmdecode
from utils.utils import time_label, logfile, get_project_root, debug


# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/imap.py
# CREDIT: @byt3bl33d3r

class ImapEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        if self.debug:
            debug(f"{self.__class__.__name__}: Initializing")

        self.target = target

    def setup(self, **kwargs):
        pass

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def validate(self) -> tuple:
        if self.target.find(":") > -1:
            host, port = self.target.split(":")
        else:
            host, port = self.target, 993
        try:
            server = imapclient.IMAPClient(self.target, port=port, ssl=True, timeout=3)
            server.login("IWouldNeverExistOnThisServer", "IWouldNeverBeAValidPassword")
        except Exception as e:
            return e == imapclient.exceptions.LoginError, e

    def login(self, username, password) -> tuple:
        host, port = self.target.split(":")
        if not port:
            port = 993
        try:
            server = imapclient.IMAPClient(self.target, port=port, ssl=True, timeout=3)
            server.login(username, password)
            return True, 0
        except imapclient.exceptions.LoginError:
            return False, 0
        except Exception as e:
            pass