import os
import uuid

from db.enums.errors import AadError
from enumerators.interfaces.enumerator import VpnEnumerator

from utils.utils import logfile, get_project_root, error, is_subdomain, extract_domain, \
    debug

# Disclaimer
# The code for the OWA enumerator has been copied and adapted from SprayingToolkit
# https://github.com/byt3bl33d3r/SprayingToolkit/blob/master/core/sprayers/owa.py
# CREDIT: @byt3bl33d3r


class MsgraphEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        if self.debug:
            debug(f"{self.__class__.__name__}: Initializing")

        self.target = target
        self.auth_url = "https://login.microsoft.com/common/oauth2/token"
        self.user_realm = None

    def setup(self, **kwargs):
        bkp = kwargs.copy()
        di = kwargs.get("Domain")
        if not self.user_realm:
            self.user_realm = di.get("Microsoft", {}).get("UserRealm")
        if not self.user_realm:
            _, _ = self.get_user_realm()
        di["Microsoft"]["UserRealm"] = self.user_realm
        bkp["Domain"] = di
        if bkp != kwargs:
            self.additional_info = bkp
            self.has_new_info = True

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def get_user_realm(self) -> tuple:
        domain = extract_domain(self.target)

        if is_subdomain(domain):
            return False, None
        url = f"https://login.microsoftonline.com:443/getuserrealm.srf?login={domain}"
        res = None
        try:
            res = self.session.get(url)
            user_realm = res.json()
            self.user_realm = user_realm
            return True, res
        except:
            return False, res

    def validate(self) -> tuple:
        b, r = self.get_user_realm()
        if not self.user_realm and not b:
            return False, r
        return "NameSpaceType" in self.user_realm.keys() and self.user_realm.get("NameSpaceType") in ["Unknown", "Managed"], r

    def get_error(self, error):
        return AadError.from_str(error)

    def login(self, username, password) -> tuple:
        data = {
            "client_id": str(uuid.uuid4()),
            "grant_type": "password",
            "resource": "https://graph.windows.net",
            "scope": "openid",
            "username": username,
            "password": password
        }
        ua = self.session.headers.get("User-Agent")
        self.session.headers["User-Agent"] = "Windows-AzureAD-Authentication-Provider/1.0"
        res = self.session.post(self.auth_url, data=data)
        self.session.headers["User-Agent"] = ua
        auth_data = res.json()
        err = None
        if "access_token" in auth_data.keys():
            return True, res
        if "error_description" in auth_data.keys():
            err = self.get_error(auth_data["error_description"])
        if err == AadError.MFA_NEEDED:
            error(f"{username} need MFA", indent=2)
            return True, res
        elif err == AadError.LOCKED:
            error(f"{username} is locked", indent=2)
            return True, res
        return False, res

