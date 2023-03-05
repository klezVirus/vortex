import argparse
import os.path
from urllib3.exceptions import InsecureRequestWarning

from enumerators.interfaces.api import Api
from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.unified_user_data import UnifiedUserData
from utils.utils import *


class Snusbase(Searcher, Api):
    def __init__(self):
        super().__init__()
        self.csrf_token = None
        self.emails: list = []

    def setup(self, **kwargs):
        self.emails = kwargs.get("emails", [])

    def save_session(self):
        try:
            self.uu_data.save_csv(os.path.join("data", f"snusbase-{time_label()}.csv"))
        except Exception as e:
            warning(e)

    def login(self):
        url = "https://snusbase.com:443/login"
        self.session.get(url)
        data = {"login": self.username, "password": self.password, "action_login": ''}
        res = self.session.post(url, data=data)
        return res.status_code == 200 and res.url.find("dashboard") > -1

    def csrf(self):
        url = "https://snusbase.com/search"
        res = self.session.get(url)
        soup = std_soup(res)
        self.csrf_token = soup.find("input", {"name": "csrf_token"})

    def __search(self, email):
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
            u = UnifiedUserData(
                name=email,
                db=db,
            )
            self.uu_data.append(u)

    def __extract_count(self, res):
        soup = std_soup(res)
        count = 0
        try:
            count = int(soup.find("span", {"id": "result_count"}).text.strip())
        except ValueError:
            pass
        return count

    def __extract_db(self, res):
        soup = std_soup(res)
        dbs = []
        try:
            dbs = list(set([x.text.split(" ")[0] for x in soup.find_all("div", {"id": "topBar"})]))
        except Exception:
            pass
        return dbs

    @staticmethod
    def execute_routine(users: list, workspace: str = None):
        snusbase = Snusbase()
        snusbase.setup(emails=users)
        snusbase.search()
        return snusbase.uu_data

    def search(self):
        # Login
        self.login()
        # Save Anti-CSRF token
        self.csrf()
        # Search mails
        for email in self.emails:
            try:
                self.__search(email)
            except:
                warning(f"Error: Skipping {email}")
                continue
        if len(self.uu_data) > 0:
            success("Saving found leaks")
            self.save_session()



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
