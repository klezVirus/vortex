import configparser
from typing import Union, Any

import boto3
from tabulate import tabulate

from lib.Sublist3r.sublist3r import PortScanner
from utils.managers.fire import FireProx
from utils.utils import *
from multiprocessing import Process, Queue
from timeit import default_timer as timer
from datetime import timedelta


class OxyManager:
    def __init__(self, **kwargs):
        self.client = boto3.client('ec2')
        self.credentials = {"accounts": []}
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(str(get_project_root().joinpath("config", ".aws", "credentials")))
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
        self.load_proxies()

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

    def check_status(self):
        result_table = []
        origins = [proxy.split("://")[1] for proxy in self.proxies]
        scanner = PortScanner(origins=origins)
        scanner.run()
        counter = 0
        for o in origins:
            if o in scanner.origins:
                result_table.append([o, "OK"])
            else:
                result_table.append([o, "FAIL*"])
                _ = self.proxies.pop(counter)
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

