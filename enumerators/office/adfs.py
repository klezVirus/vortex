import os
import uuid

from enumerators.interfaces.enumerator import VpnEnumerator
from bs4 import BeautifulSoup

from utils.utils import logfile, get_project_root, success, debug, extract_domain, extract_main_domain, \
    is_subdomain


class AdfsEnumerator(VpnEnumerator):
    def __init__(self, target, group=None):
        super().__init__()
        self.urls = [f"{target.strip()}"]
        self.user_realm = None
        self.auth_url_response = None

    def setup(self, **kwargs):
        di = kwargs.get("Domain")
        if "Microsoft" not in di.keys():
            di["Microsoft"] = {}
        self.user_realm = di.get("Microsoft", {}).get("UserRealm")
        if di.get("Microsoft", {}).get("AuthURL", None) and len(self.urls) == 0:
            self.urls = [di.get("Microsoft", {}).get("AuthURL")]
        super().setup(**kwargs)

    def login(self, username, password) -> tuple:
        if not self.target:
            return False, None
        form = None
        res = self.session.get(self.target)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, features="html.parser")
            form = soup.find("form", {"id": "loginForm"})
        if not form or not form.has_attr("action"):
            debug("Something went wrong recovering the login URL+uuid")
            client_request_id = str(uuid.uuid4())
            url = f"{res.url}&client-request-id={client_request_id}"
        else:
            url = "/".join(res.url.split("/")[:3]) + form["action"]

        data = {
            "UserName": username,
            "Password": password,
            "AuthMethod": "FormsAuthentication"
        }

        res = self.session.post(url, data=data)
        if len(res.history) > 0 and res.history[-1].status_code == 302:
            return True, res
        elif res.text.find("Your password has expired") > -1:
            success(f"{username}:{password} is valid but the password has expired")
            return True, res
        return False, res
