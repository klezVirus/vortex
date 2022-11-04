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

from utils.utils import *


class LeakedAccount:
    HEADERS = ["Email", "Db", "Data"]

    def __init__(self, email, db, data):
        self.email = email
        self.db = db
        self.data = data

    def to_csv(self):
        return f"\"{self.db}\",\"{self.email}\",\"{self.data}\""


class LeakedAccountList:
    def __init__(self):
        self.la_list = []
        self.mode = "w"

    # adding two objects
    def __add__(self, o):
        if not hasattr(o, "la_list"):
            return
        self.la_list += o.la_list
        return self

    def __len__(self):
        return len(self.la_list)

    @property
    def count(self):
        return len(self.la_list)

    def append(self, obj: LeakedAccount):
        self.la_list.append(obj)

    def to_csv(self):
        return "\n".join([obj.to_csv() for obj in self.la_list])

    def save_csv(self, filename):
        """
        This function saves the list using the following algorithm
        1st call: Writes header and overwrite the file
        2nd+ calls: Writes in append mode
        Every call to this function flushes the list of employees
        """
        if self.mode == "w":
            with open(filename, self.mode, encoding="latin-1", errors="replace") as save:
                save.write(",".join(LeakedAccount.HEADERS) + "\n")
        self.mode = "a"
        with open(filename, self.mode, encoding="latin-1", errors="replace") as save:
            save.write(self.to_csv())


class Snusbase:
    def __init__(self, username=None, password=None, config: configparser.ConfigParser = None):
        self.username = username
        self.password = password
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3", "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://snusbase.com",
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

        api_config_file = get_project_root().joinpath(self.config.get("API", "config")).absolute()
        if not api_config_file.is_file() and not (self.username and self.password):
            error("No config file found, and no credentials provided")
            exit(1)

        self.api_config = configparser.ConfigParser(allow_no_value=True,
                                                    interpolation=configparser.ExtendedInterpolation())
        self.api_config.read(str(api_config_file))

        self.username = self.api_config.get("SNUSBASE", "username")
        self.password = self.api_config.get("SNUSBASE", "password")

        self.session = requests.session()
        self.session.verify = False
        self.session.headers = self.headers
        self.results = 0
        self.leaked_account = LeakedAccountList()
        self.filter = None
        self.csrf_token = None

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

    def save_session(self):
        try:
            self.leaked_account.save_csv(os.path.join("data", f"snusbase-{time_label()}.csv"))
        except Exception as e:
            warning(e)

    @staticmethod
    def std_soup(res):
        return BeautifulSoup(res.text, features="html.parser")

    def login(self):
        url = "https://snusbase.com:443/login"
        self.session.get(url)
        data = {"login": self.username, "password": self.password, "action_login": ''}
        res = self.session.post(url, data=data)
        return res.status_code == 200 and res.url.find("dashboard") > -1

    def csrf(self):
        url = "https://snusbase.com/search"
        res = self.session.get(url)
        soup = Snusbase.std_soup(res)
        self.csrf_token = soup.find("input", {"name": "csrf_token"})

    def search(self, email):
        url = "https://snusbase.com:443/search"
        data = {
            "csrf_token": self.csrf_token,
            "term": email,
            "wildcard": "on",
            "searchtype": "email"
        }
        res = self.session.post(url, data=data)
        for db in self.__extract_db(res):
            success(f"Found {email} in {db}")
            self.leaked_account.append(
                LeakedAccount(
                    email=email,
                    db=db,
                    data=""
                )
            )

    def __extract_count(self, res):
        soup = Snusbase.std_soup(res)
        count = 0
        try:
            count = int(soup.find("span", {"id": "result_count"}).text.strip())
        except ValueError:
            pass
        return count

    def __extract_db(self, res):
        soup = Snusbase.std_soup(res)
        dbs = []
        try:
            dbs = list(set([x.text.split(" ")[0] for x in soup.find_all("div", {"id": "topBar"})]))
        except Exception:
            pass
        return dbs

    @staticmethod
    def execute_routine(emails: list):
        collector = None
        try:
            collector = Snusbase()
            # Login
            collector.login()
            # Save Anti-CSRF token
            collector.csrf()
            # Search mails
            for email in emails:
                try:
                    collector.search(email)
                except:
                    warning(f"Error: Skipping {email}")
                    continue
        except KeyboardInterrupt:
            error("Aborted by user", indent=2)
        except Exception as e:
            traceback.print_exc()
        finally:
            if collector:
                success("Saving found leaks", indent=2)
                collector.save_session()
                return collector.leaked_account


if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    parser = argparse.ArgumentParser(description="Snusbase Leak Search")
    parser.add_argument("-u", "--user", required=True, default=None,
                        help="Snusbase username")
    parser.add_argument("-p", "--password", required=True, default=None,
                        help="Snusbase password")
    parser.add_argument("emails_file", help="File with list of emails to search")
    args = parser.parse_args()

    if not os.path.isfile(args.emails_file):
        error("File not found")
        exit(1)
    emails = [m.strip() for m in open(args.emails_file, "r").readlines()]
    Snusbase.execute_routine(emails)
