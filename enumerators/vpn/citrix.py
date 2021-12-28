import json
import os

import requests
import xmltodict

from enumerators.enumerator import VpnEnumerator, ScanType
from bs4 import BeautifulSoup

from utils.utils import time_label, logfile, get_project_root, error, info


class CitrixEnumerator(VpnEnumerator):
    def __init__(self, target, group="dummy"):
        super().__init__()
        self.target = target.strip()
        self.encrypt = False
        self.session.headers["X-Citrix-Isusinghttps"] = "Yes"
        self.group = group
        self.auth_url = None
        self.auth_method = None
        self.select_auth_method()
        self.data = {}
        self.fetch_auth_configuration()

    def logfile(self, st: ScanType) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data").joinpath(logfile(fmt=fmt, script=__file__, scan_type=st.name)))

    def validate(self) -> bool:
        url = f"https://{self.target}/logon/LogonPoint/index.html"
        res = self.session.get(url, timeout=5)
        if res.status_code != 200:
            return False
        soup = BeautifulSoup(res.text, features="html.parser")
        element = soup.find_all("span", {"class": "citrixCopyright _ctxstxt_CitrixCopyright"})
        # New version of Citrix Identified
        return len(element) > 0 and len(res.history) == 0 and res.url == url

    def fetch_auth_configuration(self):
        url = f"https://{self.target}{self.auth_method}"
        self.session.headers["Origin"] = f"https://{self.target}"
        res = self.session.post(url)
        try:
            xml_content = xmltodict.parse(res.content)
            for x in xml_content["AuthenticateResponse"]["AuthenticationRequirements"]["Requirements"]["Requirement"]:
                if "Credential" not in x or "Input" not in x:
                    continue
                if "ID" not in x["Credential"].keys():
                    continue
                param = x["Credential"]["ID"]
                self.data[param] = None
                for key, value in x["Input"].items():
                    if key in ["Button", "CheckBox", "Text"]:
                        if isinstance(value, str):
                            self.data[param] = value
                        else:
                            if "InitialValue" in value.keys():
                                self.data[param] = value["InitialValue"]
        except:
            error(f"{self.__class__.__name__}: Unable to gather login parameters")

    def check_encryption(self):
        url = f"https://{self.target}/nf/auth/getECdetails"
        res = self.session.get(url)
        body = None
        try:
            body = res.json()
        except json.decoder.JSONDecodeError:
            pass
        if res.status_code == 200 and body and "encrypt" in body.keys():
            if body["encrypt"].upper() != "DISABLED":
                self.encrypt = True

    def select_auth_method(self):
        urls = self.find_auth_methods()
        if len(urls) == 0:
            return
        if len(urls) == 1:
            self.auth_method = urls[0]["url"]
        else:
            info("Select an auth method:")
            choice = -1

            for n, g in enumerate(urls, start=0):
                print(f"{n} : {g['name']} -> {g['url']}")
            while choice < 0 or choice > len(urls) - 1:
                try:
                    choice = int(input("  $> "))
                except KeyboardInterrupt:
                    exit(1)
                except ValueError:
                    pass
            self.auth_method = urls[choice]["url"]

    def find_auth_methods(self):
        url = f"https://{self.target}/cgi/GetAuthMethods"
        res = self.session.post(url)
        auth_urls = []
        try:
            xml_content = xmltodict.parse(res.content)
            if xml_content:
                for x in xml_content["authMethods"]["method"]:
                    auth_urls.append({"name": x["@url"], "url": x["@url"]})
        except:
            pass
        return auth_urls

    def find_groups(self):
        url = f"https://{self.target}/logon/LogonPoint/index.html"
        res = self.session.get(url)
        if res.status_code != 200:
            error(f"{self.__class__.__name__}: Failed to enumerate groups")
            return
        soup = BeautifulSoup(res.text, features="html.parser")
        options = soup.find_all("option")
        if len(options) == 0:
            error("No available VPN groups")
            exit(1)
        return [o["value"] for o in options]

    def select_group(self):
        groups = self.find_groups()
        info("Select a VPN group:")
        choice = -1

        for n, g in enumerate(groups, start=0):
            print(f"{n} : {g}")
        while choice < 0 or choice > len(groups) - 1:
            try:
                choice = int(input("  $> "))
            except KeyboardInterrupt:
                exit(1)
            except ValueError:
                pass
        self.group = groups[choice]

    def login(self, username, password) -> bool:
        url = f"https://{self.target}/p/u/doAuthentication.do"
        self.session.headers["X-Citrix-Am-Labeltypes"] = "none, plain, heading, information, warning, error, " \
                                                         "confirmation, image, nsg-epa, nsg-epa-failure, " \
                                                         "nsg-login-label, tlogin-failure-msg, nsg-tlogin-heading, " \
                                                         "nsg-tlogin-single-res, nsg-tlogin-multi-res, nsg-tlogin, " \
                                                         "nsg-login-heading, nsg-fullvpn, nsg-l20n, nsg-l20n-error, " \
                                                         "certauth-failure-msg, dialogue-label, " \
                                                         "nsg-change-pass-assistive-text, nsg_confirmation, " \
                                                         "nsg_kba_registration_heading, " \
                                                         "nsg_email_registration_heading, " \
                                                         "nsg_kba_validation_question, nsg_sspr_success, nf-manage-otp "
        self.session.headers["X-Citrix-Am-Credentialtypes"] = "none, username, domain, password, newpassword, " \
                                                              "passcode, savecredentials, textcredential, webview, " \
                                                              "nsg-epa, nsg-x1, nsg-setclient, nsg-eula, nsg-tlogin, " \
                                                              "nsg-fullvpn, nsg-hidden, nsg-auth-failure, " \
                                                              "nsg-auth-success, nsg-epa-success, nsg-l20n, GoBack, " \
                                                              "nf-recaptcha, ns-dialogue, nf-gw-test, nf-poll, " \
                                                              "nsg_qrcode, nsg_manageotp, negotiate, nsg_push, " \
                                                              "nsg_push_otp, nf_sspr_rem "
        data = self.data
        data["login"] = username
        data["passwd"] = password
        res = self.session.post(url, data=data)
        success = True
        if res.status_code == 200:
            try:
                xml_content = xmltodict.parse(res.content)
                if xml_content:
                    for x in xml_content["AuthenticateResponse"]["AuthenticationRequirements"]["Requirements"]["Requirement"]:
                        if "Credential" not in x:
                            continue
                        if "ID" not in x["Credential"].keys():
                            continue
                        if x["Credential"]["ID"] == "nsg-auth-failure":
                            success = False
                            break
            except:
                return False
            return success
        else:
            return False
