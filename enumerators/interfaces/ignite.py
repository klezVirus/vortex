import configparser
import json
import logging
import os
import queue
import random
import threading
import uuid
from abc import ABC, abstractmethod
from collections import deque
from threading import Event
from typing import Union

import requests
import requests_html
from urllib3.exceptions import InsecureRequestWarning

from utils.managers.aws import AWSManager
from utils.managers.oxygen import OxyManager
from utils.utils import generate_id, generate_ip, generate_trace_id, get_project_root, get_random_user_agent, logfile, \
    info, success


class Ignite(ABC):
    """
    This interface is used to define the basic methods that must be implemented by all enumerators.
    It also offers a unified way for all network agents to set up and configure AWS Api Gateways, Open proxies
    or other network layers for advanced enumeration.
    """
    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        self.__headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "close"
        }

        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(str(get_project_root().joinpath("config", "config.ini")))

        self.queue = queue.Queue()
        self.delay = float(self.config.get("NETWORK", "delay"))
        self.threads = int(self.config.get("NETWORK", "threads"))
        self.base = float(self.config.get("THROTTLE", "base"))
        self.throttle = float(self.config.get("THROTTLE", "throttle"))
        self.retry = int(self.config.get("NETWORK", "retry"))
        self.operation_max_time = int(self.config.get("OPERATION", "end_time"))
        self.lock = threading.BoundedSemaphore(self.threads)

        self.session = requests.session()
        self.session.verify = False
        self.session.headers = self.__headers
        self.session.max_redirects = 2
        self.default_passwords = []
        self.debug = int(self.config.get("DEBUG", "developer")) > 0
        self.logger = logging.Logger(name="vortex")
        handler = logging.FileHandler(self.logfile(), mode="a")
        self.logger.addHandler(handler)
        self.logger.setLevel(level=logging.INFO if not self.debug else logging.DEBUG)
        self.found = []
        self.group = None
        self.dao = None
        self.event_group_selected = Event()
        self.additional_info = None
        self.has_new_info = False
        self.aws_manager: Union[None, AWSManager] = None
        self.oxy_manager = OxyManager()
        self.urls: Union[deque, None] = None
        self.lock = threading.Lock()

    @property
    def target(self):
        # If no manager, we have one URL only
        if self.aws_manager is None:
            return self.urls[0]
        # If manager is present, we have a list of URLs
        # return the first and rotate
        self.lock.acquire()
        url = self.urls.pop()
        self.urls.append(url)
        self.lock.release()
        return url

    def add_found(self, what):
        self.lock.acquire()
        self.found.append(what)
        self.lock.release()

    def on_fire(self):
        # Change proxy if multi-proxy is enabled
        if self.oxy_manager.proxy_enabled:
            self.toggle_proxy()

        # Refresh headers if AWS is enabled
        if self.aws_manager is None:
            return
        self.session.headers["User-Agent"] = get_random_user_agent()
        self.session.headers["X-My-X-Amzn-Trace-Id"] = generate_trace_id()
        self.session.headers["X-My-X-Forwarded-For"] = generate_ip()
        self.session.headers["x-amzn-apigateway-api-id"] = generate_id()
        self.session.headers["X-My-X-Amzn-Trace-Id"] = generate_trace_id()
        self.session.headers['client-request-id'] = str(uuid.uuid4())
        self.session.headers['return-client-request-id'] = 'true'

    def logfile(self) -> str:
        fmt = os.path.basename(self.config.get("LOGGING", "file"))
        return str(get_project_root().joinpath("data", "log").joinpath(logfile(fmt=fmt, script=self.__class__.__name__)))

    def setup_awsm(self, url: str, **kwargs):
        self.aws_manager = AWSManager(**kwargs)
        self.aws_manager.load_apis(url=url)
        self.urls = self.aws_manager.list_urls(url=url)

    def stats(self):
        if self.aws_manager:
            self.aws_manager.display_stats()

        info(f"Valid objects identified: {len(self.found)}")
        for cred in self.found:
            success(f"{json.dumps(cred)}")

    @abstractmethod
    def setup(self, **kwargs):
        pass

    def tear_down(self):
        if self.aws_manager is not None:
            self.aws_manager.clear_all_apis()

    @property
    def random_throttle(self):
        return self.delay + random.uniform(0, self.throttle)

    def set_thread(self, value: int):
        self.threads = value

    def toggle_proxy(self, proxy=True):
        if not proxy:
            self.session.proxies = None
            return

        proxy = self.oxy_manager.get_proxy()

        self.session.proxies = {
            "http": proxy,
            "https": proxy
        } if proxy is not None else None
