import argparse
import json
import socket

import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning
from stem import Signal
from stem.control import Controller


class PwnDB:
    def __init__(self, domain, socks_port=None):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3", "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://pwndb2am4tzkvold.onion",
            "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1", "Te": "trailers",
            "Connection": "close"
        }
        # Domain to search against
        self.domain = domain
        self.pwndb_url = "http://pwndb2am4tzkvold.onion"
        self.session = requests.session()
        self.session.verify = False
        self.session.headers = self.headers
        # We need TOR for this
        self.socks_port = socks_port
        if not self.socks_port or self.socks_port == "":
            self.auto_select()
        self.toggle_proxy(f"socks5h://127.0.0.1:{self.socks_port}")
        try:
            self.authenticate()
        except:
            pass

    def auto_select(self):
        for port in [9050, 9150]:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            location = ("127.0.0.1", port)
            if s.connect_ex(location) == 0:
                self.socks_port = port
        if not self.socks_port:
            raise ConnectionError("Tor Service Not Listening on known ports")

    def toggle_proxy(self, proxy=None):
        if self.session.proxies is not None and proxy is None:
            self.session.proxies = None
        else:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }

    def authenticate(self):
        with Controller.from_port(port=9151) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)

    def fetch(self):
        data = {
            "luser": "",
            "domain": self.domain,
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
        return leaks


if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    parser = argparse.ArgumentParser(description="PwnDB Leaks Extractor (Requires TOR)")
    parser.add_argument("domain", help="Target Company Domain")
    args = parser.parse_args()

    pwn = PwnDB(domain=args.domain)
    leaks = pwn.fetch()
    print(json.dumps(leaks, indent=2))
