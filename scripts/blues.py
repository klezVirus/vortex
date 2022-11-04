# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import argparse
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
from bs4 import BeautifulSoup
from html import unescape
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tqdm import tqdm

from utils.utils import info, error, success, progress, get_project_root, warning


class UrnNotFoundError(Exception):
    pass


class Filter:
    def __init__(self, location):
        self.location = GeoUrn.from_name(location)

    def to_string(self):
        return f"&geoUrn=[\"{self.location}\"]"


class GeoUrn:
    UK = 101165590
    UK_England = 102299470
    UK_Scotland = 100752109
    US = 103644278
    IN = 102713980
    SKO = 105149562
    IE = 104738515

    @staticmethod
    def from_name(location):
        location = location.upper()
        if location == "IE":
            return GeoUrn.IE
        if location == "UK":
            return GeoUrn.UK
        if location == "US":
            return GeoUrn.US
        if location == "SKO":
            return GeoUrn.SKO
        if location == "IN":
            return GeoUrn.IN
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


class Employee:
    HEADERS = ["Name", "Role", "Location", "Summary"]

    def __init__(self, name, role, location, text):
        self.name = name
        self.role = role
        self.location = location
        self.text = text

    def to_csv(self):
        return f"\"{self.name}\",\"{self.role}\",\"{self.location}\",\"{self.text}\""


class EmployeeList:
    def __init__(self):
        self.employee_list = []
        self.mode = "w"

    # adding two objects
    def __add__(self, o):
        if not hasattr(o, "employee_list"):
            return
        self.employee_list += o.employee_list
        return self

    def __len__(self):
        return len(self.employee_list)

    @property
    def count(self):
        return len(self.employee_list)

    def append(self, employee: Employee):
        self.employee_list.append(employee)

    def to_csv(self):
        return "\n".join([employee.to_csv() for employee in self.employee_list])

    def save_csv(self, filename, reset=True):
        """
        This function saves the list using the following algorithm
        1st call: Writes header and overwrite the file
        2nd+ calls: Writes in append mode
        Every call to this function flushes the list of employees
        """
        if self.mode == "w":
            with open(filename, self.mode, encoding="latin-1", errors="replace") as save:
                save.write(",".join(Employee.HEADERS) + "\n")
        self.mode = "a"
        with open(filename, self.mode, encoding="latin-1", errors="replace") as save:
            save.write(self.to_csv())
        if reset:
            self.employee_list = []


class LinedInFactory:
    @staticmethod
    def from_config(file):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(file)
        session_file = config.get("LINKEDIN", "session")
        session = get_project_root().joinpath("data", "temp", session_file)
        username = config.get("LINKEDIN", "username")
        password = config.get("LINKEDIN", "password")
        use_proxy = int(config.get("NETWORK", "enabled")) != 0
        proxy = config.get("NETWORK", "proxy")

        collector = None
        session_restored = False

        if session and os.path.isfile(session):
            info("Session file found. Do you want to restore it?", indent=2)
            choice = "x"
            while choice.lower() not in ["y", "n"]:
                choice = input("  [y|n] > ")
            if choice.lower() == "y":
                try:
                    collector = LinkedIn.from_session(session)
                    session_restored = True
                except LinkedInInvalidSessionFileError:
                    error("The session file was invalid", indent=2)

        if username and password and not session_restored:
            collector = LinkedIn(username=username, password=password)

        if not collector:
            raise LinkedInInitFailed

        if use_proxy:
            collector.toggle_proxy(proxy)

        return collector


class LinkedIn:
    def __init__(self, username, password, config: configparser.ConfigParser = None):
        self.username = username
        self.password = password
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3", "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://www.linkedin.com",
            "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1", "Te": "trailers",
            "Connection": "close"
        }

        if config:
            self.config = config
        else:
            self.config = configparser.ConfigParser(allow_no_value=True,
                                                    interpolation=configparser.ExtendedInterpolation())
            self.config.read("config\\config.ini")

        self.session = requests.session()
        self.session.verify = False
        self.session.headers = self.headers
        self.results = 0
        self.employees = EmployeeList()
        self.past_employees = EmployeeList()
        self.__checkpoint = random.randint(20, 100)
        self.__current_page = 1
        self.filter = None

    @property
    def checkpoint(self):
        return self.__current_page == self.__checkpoint

    def next_checkpoint(self):
        self.__checkpoint += random.randint(20, 100)

    def toggle_proxy(self, proxy=None):
        if self.session.proxies is not None and proxy is None:
            self.session.proxies = None
        else:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }

    def add_filter(self, f):
        self.filter = f

    def save_session(self, reset=True):
        data = {
            "username": self.username,
            "password": self.password,
            "session": self.session
        }
        try:
            self.employees.save_csv(self.config.get("LINKEDIN", "employees"), reset=reset)
            self.past_employees.save_csv(self.config.get("LINKEDIN", "past_employees"), reset=reset)
            with open(self.config.get("LINKEDIN", "session"), "wb") as session:
                pickle.dump(data, session)
        except Exception as e:
            warning(e)

    @staticmethod
    def from_session(session_file):
        try:
            with open(session_file, "rb") as session:
                data = pickle.load(session)
            collector = LinkedIn(data["username"], data["password"])
            collector.session = data["session"]
            return collector
        except:
            raise LinkedInInvalidSessionFileError

    @staticmethod
    def std_soup(res):
        return BeautifulSoup(res.text, features="html.parser")

    def validate_session(self):
        url = "https://www.linkedin.com/notifications/"
        res = self.session.get(url)
        if len(res.history) > 0 and any([r.status_code == 302 for r in res.history]):
            raise LinkedInSessionExpired
        return True

    def login_prefetch(self):
        url = "https://www.linkedin.com/login/it?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin"
        res = self.session.get(url)
        soap = LinkedIn.std_soup(res)
        values = {
            "ac": soap.find("input", {"name": "ac"})["value"],
            "apfc": soap.find("input", {"name": "apfc"})["value"],
            "sIdString": soap.find("input", {"name": "sIdString"})["value"],
            "parentPageKey": soap.find("input", {"name": "parentPageKey"})["value"],
            "pageInstance": soap.find("input", {"name": "pageInstance"})["value"],
            "trk": soap.find("input", {"name": "trk"})["value"],
            "authUUID": soap.find("input", {"name": "authUUID"})["value"],
            "session_redirect": soap.find("input", {"name": "session_redirect"})["value"],
            "loginCsrfParam": soap.find("input", {"name": "loginCsrfParam"})["value"],
            "fp_data": soap.find("input", {"name": "fp_data"})["value"],
            "_d": soap.find("input", {"name": "_d"})["value"],
            "showGoogleOneTapLogin": soap.find("input", {"name": "showGoogleOneTapLogin"})["value"]
        }
        return values

    def login(self):
        url = "https://www.linkedin.com/checkpoint/lg/login-submit"
        data = self.login_prefetch()

        data["session_key"] = f"{self.username}"
        data["session_password"] = f"{self.password}"
        data["loginFlow"] = "REMEMBER_ME_OPTIN"

        res = self.session.post(url, data=data)
        if len(res.history) > 0 and any([r.status_code > 300 for r in res.history]):
            if any(["Location" in r.headers.keys() and r.headers["Location"].startswith(
                    "https://www.linkedin.com/feed/") for r in res.history]):
                # Already passed verification
                return True
            else:
                # Need to verify device
                return self.mfa_submit(res)
        return False

    @staticmethod
    def __mfa_prefetch(res):
        soup = LinkedIn.std_soup(res)
        values = {
            "csrfToken": soup.find("input", {"name": "csrfToken"})["value"],
            "challengeId": soup.find("input", {"name": "challengeId"})["value"],
            "language": soup.find("input", {"name": "language"})["value"],
            "displayTime": soup.find("input", {"name": "displayTime"})["value"],
            "challengeType": soup.find("input", {"name": "challengeType"})["value"],
            "challengeSource": soup.find("input", {"name": "challengeSource"})["value"],
            "requestSubmissionId": soup.find("input", {"name": "requestSubmissionId"})["value"],
            "challengeData": soup.find("input", {"name": "challengeData"})["value"],
            "pageInstance": soup.find("input", {"name": "pageInstance"})["value"],
            "challengeDetails": soup.find("input", {"name": "challengeDetails"})["value"],
            "failureRedirectUri": soup.find("input", {"name": "failureRedirectUri"})["value"],
            "flowTreeId": soup.find("input", {"name": "flowTreeId"})["value"],
            "signInLink": soup.find("input", {"name": "signInLink"})["value"],
            "joinNowLink": soup.find("input", {"name": "joinNowLink"})["value"],
            "_s": soup.find("input", {"name": "_s"})["value"],
            "spd": soup.find("input", {"name": "spd"})["value"] if soup.find("input", {"name": "spd"}) else "",
            "recognizedDevice": "on",
            "pin": ""
        }
        return values

    def mfa_submit(self, res):
        url = "https://www.linkedin.com:443/checkpoint/challenge/verify"

        data = LinkedIn.__mfa_prefetch(res)
        print("[*] Need to verify your device, provide your OTP")
        pin = input("    $> ")
        data["pin"] = pin
        res = self.session.post(url, data=data)
        return any(
            ["Location" in r.headers.keys() and r.headers["Location"].startswith("https://www.linkedin.com/feed/") for r
             in res.history])

    def __is_people_blob(self, blob):
        if not blob or blob == "":
            return None
        try:
            data = json.loads(blob)
            if data["data"]["metadata"]["primaryResultType"] == "PEOPLE":
                return blob
        except:

            if blob.find("primaryResultType&quot;:&quot;PEOPLE") > -1:
                return blob
            # traceback.print_exc()
            return None

    def __get_people_blob(self, url):
        res = self.session.get(url)
        if res.status_code != 200:
            return None
        soap = LinkedIn.std_soup(res)
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
            for token in name.split(" "):
                # Remove all
                if token == token.upper():
                    continue
                if token.upper() in ["PHD", "MSC", "BSC", "BS", "MS"]:
                    continue
                tokens.append(token)
            name = " ".join(tokens[:3])

            employee = Employee(name=name, role=role, location=location, text=text)
            company_tokens = company.lower().replace("-", " ").split(" ")
            if text.find("Past:") > -1 and all([role.lower().find(token) < 0 for token in company_tokens]):
                # We have to take into account local promotions
                # If the current role doesn't specify a company name, we could still get a false negative
                self.past_employees.append(employee)
            else:
                self.employees.append(employee)

    def __collect_employees_on_page(self, company_name, page_id):
        self.__current_page = page_id
        filter_string = f"&company={company_name}&keywords={company_name}"
        if self.filter:
            filter_string += self.filter.to_string()
        url = f"https://www.linkedin.com/search/results/people/?{filter_string}&origin=CLUSTER_EXPANSION&page={page_id}&sid=%40dk"
        data = self.__get_people_blob(url)
        if not data:
            return
        self.__extract_employees(data, company_name)

    def __fetch_results_count(self, company_name):
        filter_string = f"&company={company_name}&keywords={company_name}"
        if self.filter:
            filter_string += self.filter.to_string()
        url = f"https://www.linkedin.com/search/results/people/?{filter_string}&origin=CLUSTER_EXPANSION&sid=%40dk"
        data = self.__get_people_blob(url)
        if data is None:
            raise LinkedInFetchError
        return int(data["data"]["metadata"]["totalResultCount"])

    def stealth_collect_employees(self, company_name, autosave=False):
        count = self.__fetch_results_count(company_name)
        progress(f"Number of people caught by the query: {count}", indent=4)
        progress(f"Current limit: 1000", indent=4)
        count = min(1000, count)
        for page in tqdm(range(1, (count // 10) + 2)):
            self.__collect_employees_on_page(company_name, page)
            self.__wait()
        if self.employees.count > 100 and autosave:
            self.employees.save_csv("employees.csv")
        if self.past_employees.count > 100 and autosave:
            self.employees.save_csv("past_employees.csv")

    def __wait(self):
        if not self.checkpoint:
            wait = 1.0 + random.uniform(0.5, 5.0)
            time.sleep(wait)
        else:
            progress("Checkpoint reached: press Ctrl+C to exit or Enter to continue", indent=2)
            input()

    @staticmethod
    def execute_routine(target, config, location, reset=False):
        collector = None
        if not config or not os.path.isfile(config):
            error("The configuration file was not found", indent=2)
            sys.exit(1)

        try:
            collector = LinedInFactory.from_config(config)
            if location:
                f = Filter(location=location)
                collector.add_filter(f)
            try:
                collector.validate_session()
            except LinkedInSessionExpired:
                info("Logging in", indent=2)
                collector.login()
                time.sleep(2)
            info("Collecting employees data", indent=2)
            collector.stealth_collect_employees(company_name=target, autosave=reset)
        except KeyboardInterrupt:
            error("Aborted by user", indent=2)
        except LinkedInFetchError as e:
            error("Problem fetching data from LinkedIn", indent=2)
            error(f"Exception: {e}", indent=2)
        except LinkedInInitFailed:
            error("Failed to create the LinkedIn instance", indent=2)
        except Exception as e:
            traceback.print_exc()
        finally:
            if collector:
                success("Saving session to .session", indent=2)
                collector.save_session(reset=reset)
                return collector.employees + collector.past_employees


class LinkedInSessionExpired(Exception):
    pass


class LinkedInInvalidSessionFileError(Exception):
    pass


class LinkedInInitFailed(Exception):
    pass


class LinkedInFetchError(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)


if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    parser = argparse.ArgumentParser(description="Bespoke LinkedIn User Enumerator (Stealth)")
    parser.add_argument("-C", "--config", required=False, default="config.ini", help="Tool configuration file")
    parser.add_argument("-l", "--location", required=False, default=None, help="Filter for location")
    parser.add_argument("target", help="Target Company")
    args = parser.parse_args()

    LinkedIn.execute_routine(args.target, args.config, args.location)
