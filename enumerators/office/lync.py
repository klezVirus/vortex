import os
from datetime import datetime, timedelta

import requests
import xmltodict
from colorama import Fore
from requests_ntlm import HttpNtlmAuth

from db.enums.errors import AadError
from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup
import urllib.parse as urlparse

from utils.ntlmdecoder import ntlmdecode
from utils.utils import time_label, logfile, get_project_root, SimpleUTC, colors, error, debug


# Disclaimer
# The code for the Lynk enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/lynk.py
# CREDIT: @byt3bl33d3r

class LyncEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        if self.debug:
            debug(f"{self.__class__.__name__}: Initializing")
        self.target = target
        self.lync_autodiscover_url = None
        self.lync_base_url = None
        self.lync_internal_domain = None
        self.lync_auth_url = None
        if not self.find_autodiscover_url() and self.debug:
            debug(f"{self.__class__.__name__}: Couldn't detect autodiscover URL", indent=2)
        if not self.find_s4b_url() and self.debug:
            debug(f"{self.__class__.__name__}: Couldn't detect S4B URL", indent=2)
        if not self.find_s4b_domain() and self.debug:
            debug(f"{self.__class__.__name__}: Couldn't detect S4B Domain", indent=2)

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        return self.lync_autodiscover_url is not None

    def find_autodiscover_url(self):
        domain = self.target.split(":")[0]
        urls = [
            f"https://lyncdiscover.{domain}",
            f"https://lyncdiscoverinternal.{domain}"
        ]

        for url in urls:
            try:
                r = self.session.get(url)
                if r.status_code == 401 or r.status_code == 403:
                    self.lync_autodiscover_url = url
                    return True
            except ConnectionError:
                continue
            except:
                continue
        return False

    def find_s4b_url(self):
        if not self.lync_autodiscover_url:
            return False
        headers = {"Content-Type": "application/json"}
        r = requests.get(self.lync_autodiscover_url, headers=headers, verify=False).json()
        if 'user' in r['_links']:
            self.lync_base_url = r['_links']['user']['href']
        return self.lync_base_url is not None

    def find_s4b_domain(self):
        if not self.lync_base_url:
            return False
        if self.lync_base_url and 'online.lync.com' not in self.lync_base_url:
            r = self.session.get(self.lync_base_url)
            self.lync_internal_domain = r.headers['X-MS-Server-Fqdn']
        return self.lync_internal_domain is not None

    def find_auth_url(self):
        if self.lync_base_url and 'online.lync.com' not in self.lync_base_url:
            self.lync_auth_url = urlparse.urljoin('/'.join(self.lync_base_url.split('/')[0:3]), "/WebTicket/oauthtoken")
        return self.lync_auth_url is not None

    def login(self, username, password) -> bool:
        if not self.lync_auth_url:
            url = "https://login.microsoftonline.com/rst2.srf"
            data = LyncEnumerator.soap_envelop(username, password)
            self.session.headers["Content-Type"] = "application/soap+xml; charset=utf-8"
            res = self.session.post(url, data=data)
            dict_data = xmltodict.parse(res.content)
            err = None
            try:
                label = dict_data["S:Envelope"]["S:Body"]["S:Fault"]["S:Detail"]["psf:error"]["psf:internalerror"]["psf:text"].split(":")[0]
                err = AadError.from_str(label)
            except:
                pass
            if not err:
                return True
            if err == AadError.MFA_NEEDED:
                error(f"{username} need MFA", indent=2)
                return True
            elif err == AadError.LOCKED:
                error(f"{username} is locked", indent=2)
                return True
            return False
        else:
            url = self.lync_auth_url
            data = {
                "grant_type": "password",
                "username": username,
                "password": password
            }
            res = self.session.post(url, data=data)
            return "access_token" in res.json().keys()

    @staticmethod
    def soap_envelop(username, password):
        utc_times = [
            datetime.utcnow().replace(tzinfo=SimpleUTC()).isoformat(),
            (datetime.utcnow() + timedelta(days=1)).replace(tzinfo=SimpleUTC()).isoformat()
        ]
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<S:Envelope xmlns:S="http://www.w3.org/2003/05/soap-envelope" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsp="http://schemas.xmlsoap.org/ws/2004/09/policy" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:wst="http://schemas.xmlsoap.org/ws/2005/02/trust">
    <S:Header>
    <wsa:Action S:mustUnderstand="1">http://schemas.xmlsoap.org/ws/2005/02/trust/RST/Issue</wsa:Action>
    <wsa:To S:mustUnderstand="1">https://login.microsoftonline.com/rst2.srf</wsa:To>
    <ps:AuthInfo xmlns:ps="http://schemas.microsoft.com/LiveID/SoapServices/v1" Id="PPAuthInfo">
        <ps:BinaryVersion>5</ps:BinaryVersion>
        <ps:HostingApp>Managed IDCRL</ps:HostingApp>
    </ps:AuthInfo>
    <wsse:Security>
    <wsse:UsernameToken wsu:Id="user">
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password>{password}</wsse:Password>
    </wsse:UsernameToken>
    <wsu:Timestamp Id="Timestamp">
        <wsu:Created>{utc_times[0].replace('+00:00', '1Z')}</wsu:Created>
        <wsu:Expires>{utc_times[1].replace('+00:00', '1Z')}</wsu:Expires>
    </wsu:Timestamp>
</wsse:Security>
    </S:Header>
    <S:Body>
    <wst:RequestSecurityToken xmlns:wst="http://schemas.xmlsoap.org/ws/2005/02/trust" Id="RST0">
        <wst:RequestType>http://schemas.xmlsoap.org/ws/2005/02/trust/Issue</wst:RequestType>
        <wsp:AppliesTo>
        <wsa:EndpointReference>
            <wsa:Address>online.lync.com</wsa:Address>
        </wsa:EndpointReference>
        </wsp:AppliesTo>
        <wsp:PolicyReference URI="MBI"></wsp:PolicyReference>
    </wst:RequestSecurityToken>
    </S:Body>
</S:Envelope>"""
