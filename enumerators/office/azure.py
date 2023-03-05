import re
import uuid

from db.enums.errors import AadError
from enumerators.interfaces.enumerator import VpnEnumerator

from utils.utils import success, debug, generate_utc_times, error


class AzureEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = ["https://autologon.microsoftazuread-sso.com"]
        self.domain = None
        self.session.headers["Content-Type"] = "application/soap+xml; charset=utf-8"

    def setup(self, **kwargs):
        di = kwargs.get("Domain")
        # TODO: Check what is the key for the domain name only
        self.domain = di
        if kwargs.get("aws"):
            self.setup_awsm(self.target)

    def validate(self) -> tuple:
        return None, None

    def login(self, username, password) -> tuple:
        user_token_guid = "uuid-" + str(uuid.uuid4())
        message_id_guid = "urn:uuid:" + str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        url = f"{self.target}/{self.domain}/winauth/trust/2005/usernamemixed?client-request-id={request_id}"
        utc_times = generate_utc_times()
        data = rf"""<?xml version="1.0" encoding="UTF-8"?>
            <s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:u="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
              <s:Header>
                <a:Action s:mustUnderstand="1">http://schemas.xmlsoap.org/ws/2005/02/trust/RST/Issue</a:Action>
                <a:MessageID>{message_id_guid}</a:MessageID>
                <a:ReplyTo>
                  <a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
                </a:ReplyTo>
                <a:To s:mustUnderstand="1">{url}</a:To>
                <o:Security xmlns:o="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" s:mustUnderstand="1">
                  <u:Timestamp u:Id="_0">
                    <u:Created>{utc_times[0]}</u:Created>
                    <u:Expires>{utc_times[1]}</u:Expires>
                  </u:Timestamp>
                  <o:UsernameToken u:Id="{user_token_guid}">
                    <o:Username>{username}</o:Username>
                    <o:Password>{password}</o:Password>
                  </o:UsernameToken>
                </o:Security>
              </s:Header>
              <s:Body>
                <trust:RequestSecurityToken xmlns:trust="http://schemas.xmlsoap.org/ws/2005/02/trust">
                  <wsp:AppliesTo xmlns:wsp="http://schemas.xmlsoap.org/ws/2004/09/policy">
                    <a:EndpointReference>
                      <a:Address>urn:federation:MicrosoftOnline</a:Address>
                    </a:EndpointReference>
                  </wsp:AppliesTo>
                  <trust:KeyType>http://schemas.xmlsoap.org/ws/2005/05/identity/NoProofKey</trust:KeyType>
                  <trust:RequestType>http://schemas.xmlsoap.org/ws/2005/02/trust/Issue</trust:RequestType>
                </trust:RequestSecurityToken>
              </s:Body>
            </s:Envelope>
            """

        res = self.session.post(url, data=data)
        token = re.search(r"<DesktopSsoToken>(.+)</DesktopSsoToken>", res.text)
        if token:
            success(f"Found token {token} for {username}")
            return True, token.group(1)

        err = AadError.from_str(res.text)
        if err in [AadError.MFA_NEEDED, AadError.EXPIRED_PASSWORD, AadError.LOCKED]:
            error(f"ERROR: Valid user/creds, but no login {username} {err.name}")
            return True, res
        else:
            return False, res

