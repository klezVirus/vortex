# This is a sample Python script.
import re
from typing import Union

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
import tabulate
from bs4 import BeautifulSoup
from html import unescape

from selenium.webdriver.common.by import By
from tqdm import tqdm
from pyotp import TOTP

from db.enums.types import ExtendedEnum
from enumerators.interfaces.ignite import Ignite
from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.exceptions import *
from enumerators.search.structures.unified_user_data import UnifiedUserDataList, UnifiedUserData
from utils.scrapers.driver import Driver
from utils.utils import info, error, success, progress, get_project_root, warning, std_soup, debug, highlight


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


class Company:
    def __init__(self, name, urn_id, description, staff, website):
        self.name = name
        self.urn_id = urn_id
        self.description = description
        self.staff = staff
        self.website = website
        self.regions = []


class GeoUrn(ExtendedEnum):
    R00 = 'us:0'
    R01 = 'ca:0'
    R02 = 'gb:0'
    R03 = 'au:0|nz:0'
    R04 = 'cn:0|hk:0'
    R05 = 'jp:0|kr:0|my:0|np:0|ph:0|sg:0|lk:0|tw:0|th:0|vn:0'
    R06 = 'in:0'
    R07 = 'at:0|be:0|bg:0|hr:0|cz:0|dk:0|fi:0'
    R08 = 'fr:0|de:0'
    R09 = 'gr:0|hu:0|ie:0|it:0|lt:0|nl:0|no:0|pl:0|pt:0'
    R10 = 'ro:0|ru:0|rs:0|sk:0|es:0|se:0|ch:0|tr:0|ua:0'
    R11 = 'ar:0|bo:0|br:0|cl:0|co:0|cr:0|do:0|ec:0|gt:0|mx:0|pa:0|pe:0|pr:0|tt:0|uy:0|ve:0'
    R12 = 'af:0|bh:0|il:0|jo:0|kw:0|pk:0|qa:0|sa:0|ae:0'


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


class Region:
    def __init__(self, name, urn_id, count=0):
        self.name = name
        self.urn_id = urn_id
        self.count = count


class Linkedin2usernames(Searcher):
    def __init__(self):
        super().__init__()
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
        self.current_region: Union[None, Region] = None
        self.company_object: Union[None, Company] = None
        self.location = None
        self.title = None
        self.autosave = False
        self.reset = False
        self.otp = None
        self.unhandled_issues = ['captcha', 'manage-account', 'add-email']
        self.quiet = True

        self.session.headers["User-Agent"] = f"Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; SCH-I535 " \
                                             f"Build/KOT49H) AppleWebKit/534.30 (KHTML, like Gecko) " \
                                             f"Version/4.0 Mobile Safari/534.30"
        self.session.headers.update({'X-RestLi-Protocol-Version': '2.0.0'})

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
        self.quiet = kwargs.get("quiet", False)
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
            else:
                raise LinkedInInvalidSessionFileError
        except:
            raise LinkedInInvalidSessionFileError

    @staticmethod
    def from_session(session_file):
        try:
            with open(str(session_file), "rb") as session:
                data = pickle.load(session)
            collector = Linkedin2usernames()
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

    def login(self):
        url = "https://www.linkedin.com/checkpoint/lg/login-submit?loginSubmitSource=GUEST_HOME"
        data = self.login_prefetch()

        data["session_key"] = f"{self.username}"
        data["session_password"] = f"{self.password}"
        res = self.session.post(url, data=data)
        info(res.url)

        result = False
        if len(res.history) > 0 and any([r.status_code > 300 for r in res.history]):
            if Linkedin2usernames.__analyze_location_headers(res, "/feed/"):
                # Already passed verification
                result = True
            elif Linkedin2usernames.__analyze_location_headers(res, "add-phone"):
                # Skip the prompt to add a phone number
                url = 'https://www.linkedin.com/checkpoint/post-login/security/dismiss-phone-event'
                response = self.session.post(url)
                if response.status_code == 200:
                    result = True
                else:
                    result = False
            elif any(Linkedin2usernames.__analyze_location_headers(res, x) for x in self.unhandled_issues):
                result = False
            else:
                # Need to verify device
                info("Need to verify device")
                result = self.mfa_submit(res)
        if result:
            csrf_token = self.session.cookies['JSESSIONID'].replace('"', '')
            self.session.headers.update({'Csrf-Token': csrf_token})

        return result

    @staticmethod
    def __analyze_location_headers(res, word: str):
        if len(res.history) > 0 and any([r.status_code > 300 for r in res.history]):
            if any(["Location" in r.headers.keys() and
                    r.headers.get("Location", "").split("?")[0].find(word) > -1 for r in res.history]):
                # Already passed verification
                return True
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

        data = Linkedin2usernames.__mfa_prefetch(res)
        data["pin"] = self.totp.now() if self.totp else self.otp
        res = self.session.post(url, data=data)
        passed = False
        if res.text.find("Captcha") > -1:
            error("Captcha required. Please try again later.")
            return False
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

    def get_company_info(self):
        """Scrapes basic company info.
        Note that not all companies fill in this info, so exceptions are provided.
        The company name can be found easily by browsing LinkedIn in a web browser,
        searching for the company, and looking at the name in the address bar.
        """
        import urllib.parse
        escaped_name = urllib.parse.quote_plus(self.company)

        response = self.session.get(
            (
                    f'https://www.linkedin.com'
                    f'/voyager/api/organization/companies?'
                    f'q=universalName&universalName={escaped_name}'
            )
        )

        if response.status_code == 404:
            error("Could not find that company name. Please double-check LinkedIn and try again.")
            return None, 0

        if response.status_code != 200:
            error("Unexpected HTTP response code when trying to get the company info:")
            warning(f"Status code: {response.status_code}")
            return None, 0

        # Some geo regions are being fed a 'lite' version of LinkedIn mobile:
        # https://bit.ly/2vGcft0
        # The following bit is a temporary fix until I can figure out a
        # low-maintenance solution that is inclusive of these areas.
        if 'mwlite' in response.text:
            if not self.quiet:
                warning(
                    "You are being served the 'lite' version of"
                    " LinkedIn (https://bit.ly/2vGcft0) that is not yet supported"
                    " by this tool. Please try again using a VPN exiting from USA,"
                    " EU, or Australia."
                )
                error("    A permanent fix is being researched. Sorry about that!")
            raise LinkedInLiteVersionError

        try:
            response_json = json.loads(response.text)
        except json.decoder.JSONDecodeError:
            if not self.quiet:
                error("Yikes! Could not decode JSON when getting company info! :(")
                debug("Here's the first 200 characters of the HTTP reply which may help in debugging:\n\n")
                print(response.text[:200])
            raise LinkedInFetchError

        company = response_json["elements"][0]

        found_name = company.get('name', "NOT FOUND")
        found_desc = company.get('tagline', "NOT FOUND")
        found_staff = company.get('staffCount', 0)
        found_website = company.get('companyPageUrl', "NOT FOUND")

        # We need the numerical id to search for employee info. This one requires some finessing
        # as it is a portion of a string inside the key.
        # Example: "urn:li:company:1111111111" - we need that 1111111111
        found_id = company['trackingInfo']['objectUrn'].split(':')[-1]
        if not self.quiet:
            success("Company found!")
            print(tabulate.tabulate(
                [[found_name, str(found_id), found_desc, str(found_staff), found_website]],
                headers=["Name", "ID", "Description", "Staff", "Website"],
                tablefmt="fancy_grid")
            )
            info(f"Hopefully that's the right {self.company}! If not, check LinkedIn and try again.")

        self.company_object = Company(found_name, found_id, found_desc, found_staff, found_website)

        return found_id, found_staff

    def get_results(self, page):

        region = re.sub(r':', r'%3A', self.current_region.urn_id if self.current_region else "None")  # must URL encode this parameter

        # Build the base search URL.
        url = ('https://www.linkedin.com'
               '/voyager/api/search/hits'
               f'?facetCurrentCompany=List({self.company_object.urn_id})'
               f'&facetGeoRegion=List({region})'
               f'&keywords=List({self.company_object.name})'
               '&q=people&maxFacetValues=15'
               '&supportedFacets=List(GEO_REGION,CURRENT_COMPANY)'
               '&count=10'
               '&origin=organization'
               f'&start={page * 10}')

        # Perform the search for this iteration.
        result = self.session.get(url)
        return result

    def find_employees(self, result):
        """
        Takes the text response of an HTTP query, convert to JSON, and extracts employee details.
        Returns a list of dictionary items, or False if none found.
        """
        try:
            result_json = json.loads(result)
        except json.decoder.JSONDecodeError:
            if not self.quiet:
                print("\n[!] Yikes! Could not decode JSON when scraping this loop! :(")
                print("I'm going to bail on scraping names now, but this isn't normal. You should "
                      "troubleshoot or open an issue.")
                print("Here's the first 200 characters of the HTTP reply which may help in debugging:\n\n")
                print(result[:200])
            raise LinkedInFetchError

        # When you get to the last page of results, the next page will have an empty
        # "elements" list.
        if not result_json['elements']:
            return False

        # The "elements" list is the mini-profile you see when scrolling through a
        # company's employees. It does not have all info on the person, like their
        # entire job history. It only has some basics.
        for body in result_json['elements']:
            profile = (body['hitInfo']
            ['com.linkedin.voyager.search.SearchProfile']
            ['miniProfile'])
            full_name = f"{profile.get('firstName')} {profile.get('lastName')}"
            # Some employee names are not disclosed and return empty. We don't want those.
            if full_name.strip() == "":
                continue
            employee = UnifiedUserData(
                name=full_name,
                role=profile['occupation']
            )
            self.uu_data.append(employee)

        return not self.uu_data.is_empty

    def __collect_regions(self) -> bool:
        _filter = self.name_filter
        if not self.name_filter:
            _filter = self.company
        self.__current_page = 1

        result = self.get_results(1)
        if result.status_code != 200:
            raise LinkedInFetchError("HTTP Error: " + str(result.status_code))

        # Commercial Search Limit might be triggered
        if "UPSELL_LIMIT" in result.text:
            raise LinkedInCommercialSearchLimitError

        return self.__extract_regions(result.text)

    def __extract_regions(self, result):
        try:
            result_json = json.loads(result)
        except json.decoder.JSONDecodeError:
            if not self.quiet:
                print("\n[!] Yikes! Could not decode JSON when scraping this loop! :(")
                print("I'm going to bail on scraping names now, but this isn't normal. You should "
                      "troubleshoot or open an issue.")
                print("Here's the first 200 characters of the HTTP reply which may help in debugging:\n\n")
                print(result[:200])
            raise LinkedInFetchError

        if not result_json['metadata']:
            return False

        for facet in result_json.get('metadata', {}).get('facets', []):
            facet_values = facet.get('facetValues', {})
            for body in facet_values:
                if body.get("count", 0) == 0:
                    continue
                self.company_object.regions.append(Region(name=body.get('displayValue'), urn_id=body.get('value'), count=body.get('count')))
        return len(self.company_object.regions) > 0

    def __collect_employees_on_page(self, page_id) -> bool:
        result = self.get_results(page_id)
        if result.status_code != 200:
            raise LinkedInFetchError("HTTP Error: " + str(result.status_code))

        # Commercial Search Limit might be triggered
        if "UPSELL_LIMIT" in result.text:
            raise LinkedInCommercialSearchLimitError

        return self.find_employees(result.text)

    def stealth_collect_employees(self, autosave=False):
        info("Getting people in company: `{}`".format(highlight(self.company)))
        company_id, count = self.get_company_info()
        progress(f"Number of people caught by the query: {count}", indent=4)
        info("Getting regions...")
        if not self.__collect_regions():
            raise LinkedInFetchError("Could not get regions")
        progress(
            f"Found employees within the following regions: "
            f"{','.join([x.name for x in self.company_object.regions])}",
            indent=2
        )
        for region in self.company_object.regions:
            self.stealth_collect_employees_in_region(region, autosave=autosave)

    def stealth_collect_employees_in_region(self, region: Region, autosave=False):
        self.current_region = region
        info(f"Getting people in region: `{highlight(region.name)}`")
        progress(f"Number of people within the region: {region.count}", indent=2)
        count = min(1000, region.count)
        if count > 1:
            progress(f"Current limit: 1000", indent=4)
            for page in tqdm(range(1, (count // 10) + 2)):
                self.__collect_employees_on_page(page)
                self.__wait()
            if self.employees.count > 100 and autosave:
                self.employees.save_csv("employees.csv")
            if self.past_employees.count > 100 and autosave:
                self.employees.save_csv("past_employees.csv")
        elif count == 1:
            progress(f"Fetching single page result", indent=4)
            self.__collect_employees_on_page(1)
            self.__wait()
        else:
            progress(f"No results", indent=4)

    def __wait(self):
        if not self.checkpoint:
            wait = 1.0 + random.uniform(0.5, 5.0)
            time.sleep(wait)
        else:
            wait = 60.0 + random.uniform(0.5, 60.0)
            progress(f"\rCheckpoint reached... waiting {wait} seconds before restarting\r")
            time.sleep(wait)

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
                r = self.login()
                time.sleep(2)
                if not r:
                    error("Login failed")
                    return 

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
        except LinkedInLiteVersionError as e:
            error("LinkedIn Lite version is not supported")
            error(f"Exception: {e}")
        except LinkedInCommercialSearchLimitError as e:
            error("LinkedIn Commercial Search Limit might be triggered")
            error(f"Exception: {e}")
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

    Linkedin2usernames.execute_routine(args.target, args.config, args.location)
