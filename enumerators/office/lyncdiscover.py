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

class LyncdiscoverEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]

    def validate(self) -> tuple:
        return self.nuclei.run()

    def login(self, username, password) -> tuple:
        return False, None