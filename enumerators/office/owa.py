import os
import traceback
from pathlib import Path

import requests
from colorama import Fore
from requests_ntlm import HttpNtlmAuth
from tldextract import tldextract

from enumerators.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.ntlmdecoder import ntlmdecode
from utils.utils import *


# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r

class OwaEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        if self.debug:
            debug(f"{self.__class__.__name__}: Initializing")
        self.target = target
        self.autodiscover_url = None
        self.netbios_domain = None
        self.internally_hosted = False
        self.open_id = None
        self.open_id_status_code = 0

    def setup(self, **kwargs):
        bkp = kwargs.copy()
        domain = extract_domain(self.target)

        di = kwargs.get("Domain")
        ei = kwargs.get("Endpoint")
        if "OWA" not in ei.keys():
            ei["OWA"] = {}

        if is_subdomain(domain):
            # Handle case of target being a subdomain "mail.example.com"
            self.autodiscover_url = ei.get("OWA", {}).get("autodiscover")
            self.netbios_domain = ei.get("OWA", {}).get("domain")
            if not self.autodiscover_url:
                self.find_autodiscover_url(domain)
                ei["OWA"]["autodiscover"] = self.autodiscover_url
            if not self.netbios_domain:
                self.find_owa_domain()
                ei["OWA"]["domain"] = self.netbios_domain
        else:
            # Handle case of target being a domain "example.com"
            self.open_id = di.get("Microsoft", {}).get("OpenID")

            if not self.open_id:
                self.fetch_open_id()
            print(domain)
            di["Microsoft"]["OpenID"] = self.open_id

        bkp["Domain"] = di
        bkp["Endpoint"] = ei

        if bkp != kwargs:
            self.additional_info = bkp
            self.has_new_info = True

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def fetch_open_id(self):
        if self.open_id:
            return None
        domain = extract_domain(self.target)
        if is_subdomain(domain):
            domain = extract_main_domain(domain)
        url = f"https://login.microsoftonline.com/{domain}/.well-known/openid-configuration"
        r = self.session.get(url)
        self.open_id = res_to_json(r)
        self.open_id_status_code = r.status_code
        return r

    def validate(self) -> tuple:
        try:
            domain = extract_domain(self.target)

            # Handle case of target being like "mail.example.com"
            if is_subdomain(domain):
                domain = self.target
                self.find_autodiscover_url(domain)
                if self.autodiscover_url is not None:
                    return self.find_owa_domain(), None
                return False, None
            # Handle case of target being like "example.com"
            else:
                r = self.fetch_open_id()
                if self.open_id_status_code == 400:
                    warning("OWA domain appears to be hosted internally")
                    return True, r
                elif self.open_id_status_code == 200:
                    return True, r
                return False, r
        except:
            traceback.print_exc()

    def find_autodiscover_url(self, domain):

        headers = {"Content-Type": "text/xml"}
        for scheme in ["http", "https"]:
            try:
                url = f"{scheme}://{domain}/autodiscover/autodiscover.xml"
                r = requests.get(
                    url,
                    headers=headers,
                    verify=False,
                    timeout=5
                )
                if r.status_code in [401, 403]:
                    self.autodiscover_url = url
                    return True
            except ConnectionError:
                continue
            except:
                continue
        return False

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
                ntlm_info, netbios_domain = None, None
                if www_auth:
                    try:
                        ntlm_info = ntlmdecode(www_auth)
                    except Exception as e:
                        debug(f'Failed to extract NTLM domain: {e}')
                if ntlm_info:
                    netbios_domain = ntlm_info.get(
                        'DNS_Domain_name',
                        ntlm_info.get(
                            'DNS_Tree_Name',
                            ntlm_info.get('NetBIOS_Domain_Name', '')
                        )
                    )

                self.netbios_domain = netbios_domain
                break
            except:
                pass
        return self.netbios_domain is not None

    def login(self, username, password) -> tuple:
        if not self.autodiscover_url:
            url = "https://outlook.office365.com/autodiscover/autodiscover.xml"
            auth = (username, password)
            valid_auth_codes = [200, 456]
        else:
            url = self.autodiscover_url
            auth = HttpNtlmAuth(username, password)
            valid_auth_codes = [200]

        self.session.headers["Content-Type"] = "text/xml"
        res = self.session.get(url, auth=auth)
        return res.status_code in valid_auth_codes, res
