import configparser
from typing import Union, Any

import boto3
import requests.exceptions
from tabulate import tabulate

from lib.Sublist3r.sublist3r import PortScanner
from utils.managers.fire import FireProx
from utils.utils import *
from multiprocessing import Process, Queue
from timeit import default_timer as timer
from datetime import timedelta


class OxyManager:
    def __init__(self, **kwargs):
        self.globals = configparser.ConfigParser(allow_no_value=True,
                                                 interpolation=configparser.ExtendedInterpolation())
        self.globals.read(str(get_project_root().joinpath("config", "config.ini")))
        self.thread_count = int(self.globals.get("NETWORK", "threads"))
        self.proxy_file = None
        self.proxy_enabled = int(self.globals.get("NETWORK", "enabled")) == 1
        self.proxies = []
        try:
            self.proxy_file = Path(self.globals.get("NETWORK", "proxy_file"))
        except Exception as e:
            error(f"Error loading proxy file: {e}")

        if self.proxy_enabled:
            self.load_proxies()
            self.check_status()

        self.__timer = timer()

    @property
    def time_elapsed(self):
        return timedelta(seconds=timer() - self.__timer)

    def load_proxies(self):
        if self.proxy_enabled:
            if not self.proxy_file or self.proxy_file and self.proxy_file.exists():
                self.proxies = [
                    x.strip() for x in self.proxy_file.read_text().splitlines()
                    if x and x.strip() != "" and x.find("://") > -1
                ]
            else:
                self.proxies = [
                    x.strip() for x in self.globals.get("NETWORK", "proxy").split(",")
                    if x and x.strip() != "" and x.find("://") > -1
                ]

    def try_proxy(self, proxy):
        if proxy is None:
            return False
        try:
            r = requests.get("https://example.com", proxies={"http": proxy, "https": proxy}, verify=False)
        except requests.exceptions.ProxyError:
            return False
        except:
            pass
        return True

    def check_status(self):
        result_table = []
        proxies = {}
        for proxy in self.proxies:
            proxies[proxy.split("://")[1]] = proxy

        origins = list(proxies.keys())
        scanner = PortScanner(origins=origins)
        scanner.action = scanner.port_scan_list
        
        scanner.run()
        counter = 0
        for o in origins:
            if o in scanner.origins and self.try_proxy(proxies.get(o)):
                result_table.append([o, "OK"])
            else:
                result_table.append([o, "FAIL*"])
                _ = self.proxies.pop(counter)
                counter -= 1
                if _.find(o) == -1:
                    raise Exception(f"Proxy {o} not found in proxy list")
            counter += 1

        print(tabulate(result_table, headers=["Proxy", "Status"]))

    def get_proxy(self):
        if self.proxy_enabled:
            if len(self.proxies) == 0:
                return None
            if len(self.proxies) == 1:
                return self.proxies[0]
            else:
                return random.choice(self.proxies)
        else:
            return None

