# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import argparse
import base64
import copy
import json
import os.path
import pickle
import random
import sys
import time
import traceback
import configparser
from enum import Enum

import requests
import requests_html
from bs4 import BeautifulSoup
from html import unescape

from selenium.webdriver.common.by import By
from tqdm import tqdm
from pyotp import TOTP

from enumerators.interfaces.ignite import Ignite
from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.exceptions import LinkedInFetchError, LinkedInInitFailed, LinkedInSessionExpired, \
    LinkedInInvalidSessionFileError, LinkedInCaptchaError

from enumerators.search.structures.unified_user_data import UnifiedUserDataList, UnifiedUserData
from utils.scrapers.driver import Driver
from utils.utils import info, error, success, progress, get_project_root, warning, std_soup


class UrnNotFoundError(Exception):
    pass


class Filter:
    def __init__(self, location, title=None, company=None):
        self.urn_id = None
        self.title = None
        self.current_company = None
        if location:
            self.urn_id = GeoUrn.from_name(location)
        if title:
            self.title = title
        if company:
            self.current_company = company

    def to_string(self):
        url_param = ""
        if self.urn_id:
            url_param += f"&geoUrn=[\"{self.urn_id}\"]"
        if self.title:
            url_param += f"&title={self.title}"
        if self.current_company:
            url_param += f"&currentCompany=[\"{self.current_company}\"]"
        return url_param


class GeoUrn:
    UK = 101165590
    UK_England = 102299470
    UK_Scotland = 100752109
    US = 103644278
    IN = 102713980
    IN_Jharkhand = 103037983
    IN_Maharashtra = 106300413
    IN_Jamshedpur = 102779754
    IN_Karnataka = 100811329
    SKO = 105149562
    IE = 104738515
    MB = 90009639

    @staticmethod
    def from_name(location):
        location = location.upper()
        if location == "IE":
            return GeoUrn.IE
        elif location == "UK":
            return GeoUrn.UK
        elif location == "US":
            return GeoUrn.US
        elif location == "SKO":
            return GeoUrn.SKO
        elif location == "IN":
            return GeoUrn.IN
        elif location.find("IN_K") > -1:
            return GeoUrn.IN_Karnataka
        elif location.find("IN_M") > -1:
            return GeoUrn.IN_Maharashtra
        elif location.find("IN_J") > -1:
            return GeoUrn.IN_Jharkhand
        raise UrnNotFoundError


class ProfileLanguage:
    English = "en"
    Korean = "ko"
    French = "fr"
    Italian = "it"
    Chinese = "ch"


class Network:
    FIRST = "F"
    SECOND = "S"
    THIRD = "O"


class Linkedin(Searcher):
    def __init__(self):
        super().__init__()
        raise NotImplementedError("This class is not not currently working")
        self.results = 0
        self.employees = UnifiedUserDataList()
        self.past_employees = UnifiedUserDataList()
        self.__checkpoint = random.randint(20, 100)
        self.__current_page = 1
        session_file = self.config.get("LINKEDIN", "session")
        self.session_file_path = get_project_root().joinpath("data", "temp", session_file)
        self.username = self.config.get("LINKEDIN", "username")
        self.totp = TOTP(self.config.get("LINKEDIN", "otp"))
        self.password = base64.b64decode(self.config.get("LINKEDIN", "password").encode()).decode()
        self.name_filter = None
        self.company = None
        self.current_company = None
        self.location = None
        self.title = None
        self.autosave = False
        self.reset = False
        self.otp = None
        self.driver = Driver()

        self.session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 " \
                                             "Firefox/110.0"

        if self.session_file_path and self.session_file_path.is_file():
            info("Session file found. Check for validity...")
            try:
                self.load_session(self.session_file_path)
            except LinkedInInvalidSessionFileError:
                error("The session file was invalid")

    def setup(self, **kwargs):
        self.location = kwargs.get("location", None)
        self.name_filter = kwargs.get("filter", None)
        self.title = kwargs.get("title", None)
        self.company = kwargs.get("company", None)
        self.current_company = kwargs.get("current_company", None)
        self.autosave = kwargs.get("autosave", None)
        self.reset = kwargs.get("reset", None)
        self.otp = kwargs.get("otp", None)
        if not self.otp:
            self.otp = self.totp.now()

    @property
    def checkpoint(self):
        return self.__current_page == self.__checkpoint

    def next_checkpoint(self):
        self.__checkpoint += random.randint(20, 100)

    def save_session(self, reset=True):
        data = {
            "username": self.username,
            "password": self.password,
            "session": self.session
        }
        try:
            self.employees.save_csv(self.config.get("LINKEDIN", "employees"), reset=reset)
            self.past_employees.save_csv(self.config.get("LINKEDIN", "past_employees"), reset=reset)
            with open(str(self.session_file_path), "wb") as session:
                pickle.dump(data, session)
        except Exception as e:
            warning(e)

    def load_session(self, session_file):
        try:
            with open(str(session_file), "rb") as session:
                data = pickle.load(session)
            collector = copy.deepcopy(self)
            collector.username = data["username"]
            collector.password = data["password"]
            collector.session = data["session"]
            if collector.validate_session():
                self.session = collector.session
            raise LinkedInInvalidSessionFileError
        except:
            raise LinkedInInvalidSessionFileError

    @staticmethod
    def from_session(session_file):
        try:
            with open(str(session_file), "rb") as session:
                data = pickle.load(session)
            collector = Linkedin()
            collector.username = data["username"]
            collector.password = data["password"]
            collector.session = data["session"]
            if collector.validate_session():
                return collector
            raise LinkedInInvalidSessionFileError
        except:
            raise LinkedInInvalidSessionFileError

    def validate_session(self):
        url = "https://www.linkedin.com/notifications/"
        res = self.session.get(url)
        if len(res.history) > 0 and any([r.status_code == 302 for r in res.history]):
            raise LinkedInSessionExpired
        return True

    def login_prefetch(self):
        url = "https://www.linkedin.com/login?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin"
        res = self.session.get(url)
        soap = std_soup(res)
        # Replace all ["value"] with get("value") to avoid KeyError
        values = {
            "ac": soap.find("input", {"name": "ac"}).get("value"),
            "apfc": soap.find("input", {"name": "apfc"}).get("value"),
            "sIdString": soap.find("input", {"name": "sIdString"}).get("value"),
            "parentPageKey": soap.find("input", {"name": "parentPageKey"}).get("value"),
            "pageInstance": soap.find("input", {"name": "pageInstance"}).get("value"),
            "trk": soap.find("input", {"name": "trk"}).get("value"),
            "authUUID": soap.find("input", {"name": "authUUID"}).get("value"),
            "session_redirect": soap.find("input", {"name": "session_redirect"}).get("value"),
            "loginCsrfParam": soap.find("input", {"name": "loginCsrfParam"}).get("value"),
            "fp_data": soap.find("input", {"name": "fp_data"}).get("value"),
            "_d": soap.find("input", {"name": "_d"}).get("value"),
            "showGoogleOneTapLogin": soap.find("input", {"name": "showGoogleOneTapLogin"}).get("value")
        }
        return values

    def login_with_selenium(self):
        self.driver.setup_method(session=self.session)
        self.driver.import_cookies_from_session()
        self.driver.open_page("https://www.linkedin.com/home")
        self.driver.find(By.ID, "session_key").send_keys(self.username)
        self.driver.find(By.ID, "session_password").send_keys(self.password)
        self.driver.find(By.CSS_SELECTOR, ".sign-in-form__submit-button").click()
        self.driver.render()
        self.driver.wait_for(By.ID, "ember18", wait_time=100000)

    def login(self):
        url = "https://www.linkedin.com/uas/login-submit"
        data = self.login_prefetch()

        data["session_key"] = f"{self.username}"
        data["session_password"] = f"{self.password}"
        data["loginFlow"] = "REMEMBER_ME_OPTIN"

        res = self.session.post(url, data=data)
        if len(res.history) > 0 and any([r.status_code > 300 for r in res.history]):
            if any(["Location" in r.headers.keys() and
                    r.headers.get("Location", "").split("?")[0].find("/feed/") > -1 for r in res.history]):
                # Already passed verification
                return True
            else:
                # Need to verify device
                return self.mfa_submit(res)
        return False

    @staticmethod
    def __mfa_prefetch(res):
        soup = std_soup(res)
        values = {
            "csrfToken": soup.find("input", {"name": "csrfToken"}).get("value"),
            "challengeId": soup.find("input", {"name": "challengeId"}).get("value"),
            "language": soup.find("input", {"name": "language"}).get("value"),
            "displayTime": soup.find("input", {"name": "displayTime"}).get("value"),
            "challengeType": soup.find("input", {"name": "challengeType"}).get("value"),
            "challengeSource": soup.find("input", {"name": "challengeSource"}).get("value"),
            "requestSubmissionId": soup.find("input", {"name": "requestSubmissionId"}).get("value"),
            "challengeData": soup.find("input", {"name": "challengeData"}).get("value"),
            "pageInstance": soup.find("input", {"name": "pageInstance"}).get("value"),
            "challengeDetails": soup.find("input", {"name": "challengeDetails"}).get("value"),
            "failureRedirectUri": soup.find("input", {"name": "failureRedirectUri"}).get("value"),
            "flowTreeId": soup.find("input", {"name": "flowTreeId"}).get("value"),
            "signInLink": soup.find("input", {"name": "signInLink"}).get("value"),
            "joinNowLink": soup.find("input", {"name": "joinNowLink"}).get("value"),
            "_s": soup.find("input", {"name": "_s"}).get("value"),
            "spd": soup.find("input", {"name": "spd"}).get("value") if soup.find("input", {"name": "spd"}) else "",
            "recognizedDevice": "on",
            "pin": ""
        }
        return values

    def mfa_submit(self, res):
        url = "https://www.linkedin.com:443/checkpoint/challenge/verify"

        data = Linkedin.__mfa_prefetch(res)
        data["pin"] = self.totp.now() if self.totp else self.otp
        res = self.session.post(url, data=data)
        passed = False
        if res.text.find("Captcha") > -1:
            self.login_with_selenium()
            self.session = self.driver.session
            passed = True
        if not passed:
            for r in res.history:
                try:
                    if "Location" in r.headers.keys() and r.headers.get("Location", "").split("?")[0].find("/feed/") > -1:
                        passed = True
                        break
                except Exception as e:
                    warning(f"Error (non-blocking): {e}")
                    continue
        return passed

    def __is_people_blob(self, blob):
        if not blob or blob == "":
            return None
        try:
            data = json.loads(blob)
            if data.get("data", {}).get("metadata", {}).get("primaryResultType") == "PEOPLE":
                return blob
        except:
            if blob.find("primaryResultType&quot;:&quot;PEOPLE") > -1:
                return blob
            traceback.print_exc()
            return None

    def __get_people_blob(self, url):
        res = self.session.get(url)
        if res.status_code != 200:
            return None
        soap = std_soup(res)
        if not soap.find("code", {"style": "display: none"}):
            # TODO: Make the 'blues' search work again. Fuck you LinkedIn.
            self.driver.setup_method(self.session, headless=True)
            _ = self.driver.open_page(url)
            self.driver.import_cookies_from_session()
            html_source = self.driver.open_page(url)
            soap = std_soup(html_source)
            data = {"included": [], "data": {"metadata": {"primaryResultType": "PEOPLE"}}}
            for code_block in soap.find_all("div", {"class": "entity-result"}):
                name = code_block.find("span", {"aria-hidden": True})
                if name:
                    name = name.get_text().strip()
                location = code_block.find("div", {"class": "entity-result__primary-subtitle t-14 t-black--light t-normal"})
                if location:
                    location = location.get_text().strip()
                role = code_block.find("div", {"class": "entity-result__primary-subtitle t-14 t-black t-normal"}).get_text().strip()
                if role:
                    role = role.get_text().strip()
                insight = code_block.find("p", {"class": "entity-result__summary entity-result__summary--2-lines t-12 t-black--light mb1"})
                if insight:
                    insight = insight.get_text().strip()
                data["included"].append({
                    "title": {"text": name},
                    "primarySubtitle": {"text": role},
                    "secondarySubtitle": {"text": location},
                    "summary": {"text": insight}
                })
        else:
            for code_block in soap.find_all("code", {"style": "display: none"}):
                blob = unescape(code_block.text)
                if self.__is_people_blob(blob) is not None:
                    return json.loads(blob)
        return None

    def __extract_employees(self, data, company):
        for d in data["included"]:
            if not d or not isinstance(d, dict) or "template" not in d.keys():
                continue
            name, role, location, text = "", "", "", ""
            try:
                name = d["title"]["text"] if "title" in d.keys() and "text" in d["title"].keys() else ""
                role = d["primarySubtitle"]["text"] if "primarySubtitle" in d.keys() and "text" in d[
                    "primarySubtitle"].keys() else ""
                location = d["secondarySubtitle"]["text"] if "secondarySubtitle" in d.keys() and "text" in d[
                    "secondarySubtitle"].keys() else ""
                text = d["summary"]["text"] if "summary" in d.keys() and "text" in d["summary"].keys() else ""
            except (KeyError, AttributeError):
                pass

            # Attempt to remove all the freaking (CPA, OSCP, OSCE, ..., PhD, MSc, ...)
            tokens = []
            for token in name.replace(".", "").split(" "):
                # Remove all
                if token == token.upper():
                    continue
                if token.upper() in ["PHD", "MBA", "BA", "MSC", "BSC", "BS", "MS", "IN", "IT"]:
                    continue
                tokens.append(token)
            name = " ".join([x.capitalize() for x in tokens[:3]])
            if name.lower().find("linkedin") > -1 or name.lower().find("helpdesk") > -1:
                continue
            if name.strip() == "":
                continue
            employee = UnifiedUserData(name=name, role=role, location=location, text=text)
            company_tokens = company.lower().replace("-", " ").split(" ")
            if text.find("Past:") > -1 and all([role.lower().find(token) < 0 for token in company_tokens]):
                # We have to take into account local promotions
                # If the current role doesn't specify a company name, we could still get a false negative
                self.past_employees.append(employee)
            else:
                self.employees.append(employee)
            print(employee.to_csv())
            self.uu_data.append(employee)

    def __collect_employees_on_page(self, page_id):
        _filter = self.name_filter
        if not self.name_filter:
            _filter = self.company
        self.__current_page = page_id
        filter_string = f"&company={self.company}&keywords={_filter}"
        if self.filter:
            filter_string += self.filter.to_string()
        url = f"https://www.linkedin.com/search/results/people/?{filter_string}&origin=CLUSTER_EXPANSION&page={page_id}&sid=%40dk"
        data = self.__get_people_blob(url)
        if not data:
            return
        self.__extract_employees(data, self.company)

    def __fetch_results_count(self):
        _filter = self.name_filter
        if not _filter:
            _filter = self.company
        filter_string = f"&company={self.company}&keywords={_filter}"
        if self.filter:
            filter_string += self.filter.to_string()
        url = f"https://www.linkedin.com/search/results/people/?{filter_string}&origin=CLUSTER_EXPANSION&sid=%40dk"
        counter = 0
        data = None
        while counter < self.retry:
            counter += 1
            data = self.__get_people_blob(url)
            if data:
                break
        if data is None:
            raise LinkedInFetchError
        return int(data["data"]["metadata"]["totalResultCount"])

    def stealth_collect_employees(self, autosave=False):
        count = self.__fetch_results_count()
        progress(f"Number of people caught by the query: {count}", indent=4)
        count = min(1000, count)
        if count > 1:
            progress(f"Current limit: 1000", indent=4)
            for page in tqdm(range(1, (count // 10) + 2)):
                self.__collect_employees_on_page(page)
                self.__wait()
            if self.employees.count > 100 and autosave:
                self.employees.save_csv("employees.csv")
            if self.past_employees.count > 100 and autosave:
                self.employees.save_csv("past_employees.csv")
        else:
            progress(f"Fetching single page result", indent=4)
            self.__collect_employees_on_page(1)
            self.__wait()

    def __wait(self):
        if not self.checkpoint:
            wait = 1.0 + random.uniform(0.5, 5.0)
            time.sleep(wait)
        else:
            progress("Checkpoint reached... waiting 1 minute before restarting")
            time.sleep(60)

    def search(self):
        info(f"Starting search on {self.__class__.__name__}")
        try:
            self.filter = Filter(
                location=self.location,
                title=self.title,
                company=self.current_company
            )
            try:
                self.validate_session()
            except LinkedInSessionExpired:
                info("Logging in")
                self.login()
                time.sleep(2)
            info("Collecting employees data")
            if isinstance(self.name_filter, str):
                _filter = [x.strip() for x in self.name_filter.split(",")]
            else:
                if isinstance(self.name_filter, list):
                    _filter = self.name_filter
                else:
                    _filter = None
            if _filter:
                for _f in _filter:
                    self.name_filter = _f
                    self.stealth_collect_employees()
            else:
                self.name_filter = None
                self.stealth_collect_employees()
        except KeyboardInterrupt:
            error("Aborted by user")
        except LinkedInFetchError as e:
            error("Problem fetching data from LinkedIn")
            error(f"Exception: {e}")
        except LinkedInCaptchaError as e:
            error("A Captcha is preventing automatic LinkedIn login")
            error(f"Exception: {e}")
        except LinkedInInitFailed:
            error("Failed to create the LinkedIn instance")
        except Exception as e:
            traceback.print_exc()
        finally:
            success("Saving session to .session")
            self.save_session(reset=self.reset)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Bespoke LinkedIn User Enumerator (Stealth)")
    parser.add_argument("-C", "--config", required=False, default="config.ini", help="Tool configuration file")
    parser.add_argument("-l", "--location", required=False, default=None, help="Filter for location")
    parser.add_argument("target", help="Target Company")
    args = parser.parse_args()

    Linkedin.execute_routine(args.target, args.config, args.location)
