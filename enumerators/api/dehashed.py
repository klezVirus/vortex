# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import argparse
import base64
import os.path
import traceback
import configparser

from db.dao.leak import LeakDao
from db.dao.user import UserDao
from db.handler import DBHandler
from db.models.leak import Leak
from db.models.user import User
from enumerators.interfaces.api import Api
from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.unified_user_data import UnifiedUserDataList, UnifiedUserData
from utils.utils import *


class Dehashed(Searcher, Api):
    def __init__(self):
        super().__init__()
        self.session.headers["Accept"] = "application/json"
        auth_token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        self.session.headers["Authorization"] = f"Basic {auth_token}"
        self.results = 0
        self.filter = None
        self.csrf_token = None
        self.domain = None

    def setup(self, **kwargs):
        self.domain = kwargs.get("domain")
        self.filter = kwargs.get("filter")

    def save_session(self):
        try:
            self.uu_data.save_csv(os.path.join("data", f"{self.__class__.__name__.lower()}-{time_label()}.csv"))
        except Exception as e:
            warning(e)

    def search(self):
        url = f"https://api.dehashed.com/search?query=domain:{self.domain}&size=10000&page=1"
        res = self.session.get(url)
        res = res.json()
        entries = res.get("entries")
        if entries is None:
            error(f"No results found")
            return
        for entry in entries:
            u = UnifiedUserData(
                name=entry.get("name"),
                phone=entry.get("phone"),
                email=entry.get("email"),
                password=entry.get("password"),
                username=entry.get("username"),
                db=entry.get("database_name"),
                phash=entry.get("hashed_password"),
                address=entry.get("address"),
            )
            self.uu_data.append(u)
        self.save_session()

    @staticmethod
    def execute_routine(domains: list, workspace: str):
        collector = None
        try:
            collector = Dehashed()
            collector.setup(domain=domains[0])
            # Search mails
            for domain in domains:
                try:
                    collector.search()
                except:
                    traceback.print_exc()
                    warning(f"Error: Skipping {domain}")
                    continue
        except KeyboardInterrupt:
            error("Aborted by user")
        except Exception as e:
            traceback.print_exc()
        finally:
            if collector:
                success("Saving found leaks")
                collector.save_session()
                return collector.uu_data


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Bespoke DeHashed API Collector")
    parser.add_argument("-w", "--workspace", required=False, default=None,
                        help="Project Workspace DB")
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
    Dehashed.execute_routine(domains, args.workspace)
