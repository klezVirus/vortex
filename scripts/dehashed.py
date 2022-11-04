# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import argparse
import base64
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

from db.dao.leak import LeakDao
from db.dao.user import UserDao
from db.handler import DBHandler
from db.models.leak import Leak
from db.models.user import User
from utils.utils import *


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

    def append(self, obj: User):
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
                save.write(",".join(["Uid", "Name", "Username", "Email", "Job", "Valid"]) + "\n")
        self.mode = "a"
        with open(filename, self.mode, encoding="latin-1", errors="replace") as save:
            save.write(self.to_csv())


class Dehashed:
    def __init__(self, workspace: str, username=None, password=None, config: configparser.ConfigParser = None):
        self.username = username
        self.password = password
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3", "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded", "Connection": "close",
            "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1", "Te": "trailers"
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

        self.username = self.api_config.get("DEHASHED", "username")
        self.password = self.api_config.get("DEHASHED", "password")

        self.session = requests.session()
        if self.config.getboolean("NETWORK", "enabled"):
            self.toggle_proxy(self.config.get("NETWORK", "proxy"))
        self.session.verify = False
        self.session.headers = self.headers
        self.session.headers["Accept"] = "application/json"
        auth_token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        self.session.headers["Authorization"] = f"Basic {auth_token}"

        self.results = 0
        self.u_dao = UserDao(DBHandler(workspace))
        self.l_dao = LeakDao(DBHandler(workspace))
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
            self.leaked_account.save_csv(os.path.join("data", f"{self.__class__.__name__.lower()}-{time_label()}.csv"))
        except Exception as e:
            warning(e)

    def search(self, domain):
        url = f"https://api.dehashed.com/search?query=domain:{domain}&size=10000&page=1"
        res = self.session.get(url)
        res = res.json()
        entries = res.get("entries")
        if entries is None:
            error(f"No results found", indent=2)
            return
        for entry in entries:
            name = entry.get('name')
            username = entry.get('username')
            email = entry.get('email')
            db = entry.get('database_name')
            hashed = entry.get("hashed_password")
            phone = entry.get("phone")
            address = entry.get("address")
            password = entry.get("password")
            info(f"Found {email} in {db}")
            try:
                uid = self.u_dao.save(
                    User(
                        uid=0,
                        email=email,
                        username=username,
                        name=name,
                        role=""
                    )
                )
                leak = Leak(
                    uid=uid,
                    leak_id=0,
                    password=password,
                    address=address,
                    phone=phone,
                    hashed=hashed,
                    database=db
                )
                progress(f"Updating DB with {leak.to_string()}", indent=2)
                self.l_dao.save(leak)
                success("User and leak inserted in DB", indent=2)
            except Exception as e:
                error(f"Exception: {e}", indent=2)

    @staticmethod
    def execute_routine(domains: list, workspace: str):
        collector = None
        try:
            collector = Dehashed(workspace)
            # Search mails
            for domain in domains:
                try:
                    collector.search(domain)
                except:
                    traceback.print_exc()
                    warning(f"Error: Skipping {domain}")
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

    parser = argparse.ArgumentParser(description="Bespoke DeHashed API Collector")
    parser.add_argument("-u", "--user", required=False, default=None,
                        help="DeHashed username")
    parser.add_argument("-p", "--password", required=False, default=None,
                        help="DeHashed password")
    parser.add_argument("domains_file", help="File with list of domains to search")
    args = parser.parse_args()

    if not os.path.isfile(args.domains_file):
        error("File not found")
        exit(1)
    domains = [m.strip() for m in open(args.domains_file, "r").readlines()]
    Dehashed.execute_routine(domains)
