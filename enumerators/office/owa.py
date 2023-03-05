import os
import traceback

from requests_ntlm import HttpNtlmAuth

from enumerators.interfaces.enumerator import VpnEnumerator

from utils.ntlmdecoder import ntlmdecode, extract_owa_domain
from utils.utils import *


# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r

class OwaEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        self.autodiscover_url = None
        self.netbios_domain = None
        self.internally_hosted = False
        self.open_id = None
        self.open_id_status_code = 0

    def setup(self, **kwargs):
        domain = extract_domain(self.target)
        ei = kwargs.get("Endpoint")
        if "OWA" not in ei.keys():
            ei["OWA"] = {}

        if is_subdomain(domain):
            # Handle case of target being a subdomain "mail.example.com"
            self.autodiscover_url = ei.get("OWA", {}).get("autodiscover")
            self.netbios_domain = ei.get("OWA", {}).get("domain")
        super().setup(**kwargs)

    def find_owa_domain(self):
        if not self.autodiscover_url:
            return False
        base_url = self.autodiscover_url.replace(
            "autodiscover/autodiscover.xml",
            ""
        )
        auth_header = {"Authorization": "NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw=="}
        owa_endpoints = []
        oef = Path(self.config.get("OWA", "endpoints")).absolute()
        if oef.is_file():
            with open(str(oef)) as fp:
                owa_endpoints = [x for x in fp.readlines() if x.strip() != ""]

        if len(owa_endpoints) == 0:
            owa_endpoints.append("autodiscover/autodiscover.xml")

        for endpoint in owa_endpoints:
            try:
                r = requests.post(base_url + endpoint, headers=auth_header, verify=False)
                www_auth = r.headers.get("WWW-Authenticate")
                self.netbios_domain = extract_owa_domain(www_auth)
                if self.netbios_domain is not None:
                    break
            except:
                pass
        return self.netbios_domain is not None

    def login(self, username, password) -> tuple:
        url = self.target + "/autodiscover/autodiscover.xml"
        auth = HttpNtlmAuth(username, password)
        valid_auth_codes = [200]

        self.session.headers["Content-Type"] = "text/xml"
        res = self.session.get(url, auth=auth)
        return res.status_code in valid_auth_codes, res
