import configparser
import json
import logging
import queue
import random
import threading
import time
import traceback
from _queue import Empty
from abc import ABC, abstractmethod
from enum import Enum
import sqlite3 as sql
from http.client import RemoteDisconnected
from pydoc import locate
from threading import Event

import requests
from colorama import Fore

from enumerators.parallel import Worker, ValidateWorker
from utils.utils import get_project_root, colors


class VpnEnumerator(ABC):
    def __init__(self):
        self.__headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Te": "trailers",
            "Connection": "close"
        }

        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(str(get_project_root().joinpath("config", "config.ini")))

        self.__queue = queue.Queue()
        self.__delay = float(self.config.get("NETWORK", "delay"))
        self.__threads = int(self.config.get("NETWORK", "threads"))
        self.__base = float(self.config.get("THROTTLE", "base"))
        self.__throttle = float(self.config.get("THROTTLE", "throttle"))
        self.__retry = int(self.config.get("NETWORK", "retry"))
        self.__lock = threading.BoundedSemaphore(self.__threads)

        self.session = requests.session()
        if int(self.config.get("NETWORK", "enabled")) != 0:
            proxy = self.config.get("NETWORK", "proxy")
            self.toggle_proxy(proxy=proxy)

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

    @abstractmethod
    def setup(self, **kwargs):
        pass

    @property
    def random_throttle(self):
        return self.__delay + random.uniform(0, self.__throttle)

    def set_thread(self, value: int):
        self.__threads = value

    def add_valid_login(self, username, password):
        self.__lock.acquire()
        self.found.append({"username": username, "password": password})
        self.__lock.release()

    def enqueue(self, value):
        self.__queue.put(value, block=True, timeout=5)

    def dequeue(self):
        try:
            return self.__queue.get(block=True, timeout=1)
        except Empty:
            return None, None

    def done(self):
        try:
            return self.__queue.task_done()
        except ValueError:
            return

    def parallel_login(self, users: list, passwords: list = None, use_leaks: bool = False):
        if not use_leaks and (passwords is None or len(passwords) == 0):
            return
        attempts = []
        for i in range(self.__threads):  # noqa
            thread = Worker()
            thread.threading_object = self
            thread.daemon = True
            thread.start()
        for user in users:
            if use_leaks:
                for leak in user.leaks:
                    if f"{user.email}:{leak}" in attempts:
                        continue
                    attempts.append(f"{user.email}:{leak}")
                    self.enqueue((user.email, leak))
            else:
                for password in passwords:
                    if f"{user.email}:{password}" in attempts:
                        continue
                    attempts.append(f"{user.email}:{password}")
                    self.enqueue((user.email, password))
        self.__queue.join()

    def safe_validate(self) -> tuple:
        retries = self.__retry
        redirects = 0
        while True:
            try:
                time.sleep(self.random_throttle)
                return self.validate()
            except requests.exceptions.TooManyRedirects:
                if redirects > 2:
                    return False, None
                redirects += 1
            except (
                requests.ReadTimeout,
                ConnectionError,
                ConnectionResetError,
                requests.exceptions.ConnectionError,
                RemoteDisconnected
            ):
                pass
            except FileNotFoundError:
                pass
            retries -= 1
            if retries == 0:
                break
        return False, None

    def safe_login(self, username, password) -> tuple:
        retries = self.__retry
        while retries > 0:
            try:
                time.sleep(self.random_throttle)
                return self.login(username, password)
            except (requests.ReadTimeout, ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects):
                retries -= 1
                pass
        return False, None

    def safe_user_enum(self, username) -> tuple:
        retries = self.__retry
        while retries > 0:
            try:
                time.sleep(self.random_throttle)
                return self.user_enum(username)
            except (requests.ReadTimeout, ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects):
                retries -= 1
                pass
        return False, None

    @abstractmethod
    def validate(self) -> tuple:
        pass

    # Not an abstract method because just a few enumerators will support it
    def user_enum(self, user) -> tuple:
        return False, None

    @abstractmethod
    def login(self, user, password) -> tuple:
        pass

    @abstractmethod
    def logfile(self) -> str:
        pass

    @staticmethod
    def from_name(name: str):
        try:
            enumerator_class_string = f"enumerators.{name}.{name.capitalize()}Enumerator"
            print(enumerator_class_string)
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class
        except:
            traceback.print_exc()
            pass

    def load_default_passwords(self, file):
        with open(file) as password_file:
            for password in password_file.read().split("\n"):
                self.default_passwords.append(password.strip())

    def toggle_proxy(self, proxy=None):
        if self.session.proxies is not None and proxy is None:
            self.session.proxies = None
        else:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }

    def attempt_login(self, username, password, quiet=False):
        result = False
        msg = f"Login with {username}:"
        msg += password
        try:
            if self.login(username, password):
                self.found.append(f"{username},{password},SUCCESS")
                msg = f"[+] {msg}... SUCCESS!"
                if not quiet:
                    print(colors(msg, Fore.GREEN))
                return True
            else:
                msg = f"[-] {msg}... FAILED"
                if not quiet:
                    print(msg)
                return False
        except KeyboardInterrupt:
            exit(1)
        except:
            return False



