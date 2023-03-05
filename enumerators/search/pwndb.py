import argparse
import json
import socket

import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning
from stem import Signal
from stem.control import Controller

from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.unified_user_data import UnifiedUserData


class Pwndb(Searcher):
    def __init__(self):
        self.pwndb_url = "http://pwndb2am4tzkvold.onion"
        self.socks_port = None
        self.domain = None
        if not self.socks_port or self.socks_port == "":
            self.auto_select()
        self.toggle_proxy(f"socks5h://127.0.0.1:{self.socks_port}")
        try:
            self.authenticate()
        except:
            pass

    def setup(self, **kwargs):
        self.domain = kwargs.get("domain")
        self.socks_port = kwargs.get("socks_port")

    def search(self):
        for d in self.domain:
            self.fetch(d)

    def auto_select(self):
        for port in [9050, 9150]:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            location = ("127.0.0.1", port)
            if s.connect_ex(location) == 0:
                self.socks_port = port
            s.close()
        if not self.socks_port:
            raise ConnectionError("Tor Service Not Listening on known ports")

    def authenticate(self):
        with Controller.from_port(port=9151) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)

    def fetch(self, domain):
        data = {
            "luser": "",
            "domain": domain,
            "luseropr": "1",
            "domainopr": "0",
            "submitform": "em"
        }

        res = self.session.post(self.pwndb_url, data=data, timeout=None)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, features="html.parser")
        if not soup.find("pre"):
            return None
        raw = soup.find("pre").text
        return self.extract(raw)

    def extract(self, raw):
        leaks = {}
        lines = raw.split("\n")
        current_user = None
        for _, line in enumerate(lines, start=0):
            if line.find("[luser]") > -1:
                current_user = line.strip().replace("[luser] => ", "").lower()
            elif line.find("[password]") > -1:
                password = line.strip().replace("[password] => ", "")
                if current_user not in leaks.keys():
                    leaks[current_user] = []
                if password not in leaks[current_user]:
                    leaks[current_user].append(password)
        for u, leak in leaks.items():
            self.uu_data.append(
                UnifiedUserData(
                    name=u,
                    password=leak
                )
            )


if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    parser = argparse.ArgumentParser(description="PwnDB Leaks Extractor (Requires TOR)")
    parser.add_argument("domain", help="Target Company Domain")
    args = parser.parse_args()

    pwn = Pwndb(domain=args.domain)
    leaks = pwn.fetch()
    print(json.dumps(leaks))
