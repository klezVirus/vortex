import configparser
import json
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

from enumerators.parallel import Worker
from utils.utils import get_project_root, colors


class ScanType(Enum):
    DEFAULTS = 0
    LEAKS = 1

    @staticmethod
    def from_name(name):
        if name.lower() in ["defaults", "default", "def", "d"]:
            return ScanType.DEFAULTS
        elif name.lower() in ["leaks", "leak", "l"]:
            return ScanType.LEAKS
        else:
            raise NotImplementedError(f"No scan types recorded for name {name}")


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
        self.debug = int(self.config.get("DEBUG", "enabled")) > 0
        self.found = []
        self.group = None
        self.event_group_selected = Event()

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

    def safe_validate(self) -> bool:
        retries = self.__retry
        redirects = 0
        while True:
            try:
                time.sleep(self.random_throttle)
                return self.validate()
            except requests.exceptions.TooManyRedirects:
                if redirects > 2:
                    return False
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
        return False

    def safe_login(self, username, password) -> tuple:
        retries = self.__retry
        while retries > 0:
            try:
                time.sleep(self.random_throttle)
                return self.login(username, password)
            except (requests.ReadTimeout, ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects):
                retries -= 1
                pass
        return False

    @abstractmethod
    def validate(self) -> bool:
        pass

    @abstractmethod
    def login(self, user, password) -> tuple:
        pass

    @abstractmethod
    def logfile(self, st: ScanType) -> str:
        pass

    @staticmethod
    def from_name(name: str):
        try:
            enumerator_class_string = f"enumerators.{name}.{name.capitalize()}Enumerator"
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

    def default_logins(self, users):
        for user in users:
            if not isinstance(user, dict) or "mail" not in user.keys():
                print(f"[-] Invalid user dictionary found: {user}")
                continue
            for default in self.default_passwords:
                self.attempt_login(user['mail'], default)

    def leaked_logins(self, users):
        for user in users:
            if not isinstance(user, dict) or "mail" not in user.keys() or "credentials" not in user.keys():
                print(f"[-] Invalid user dictionary found: {user}")
                continue
            for password in user["credentials"]:
                self.attempt_login(user['mail'], password)

    def attempt_login(self, username, password):
        result = False
        msg = f"Login with {username}:"
        msg += password
        try:
            if self.login(username, password):
                self.found.append(f"{username},{password},SUCCESS")
                msg = f"[+] {msg}... SUCCESS!"
                print(colors(msg, Fore.GREEN))
                return True
            else:
                msg = f"[-] {msg}... FAILED"
                print(msg)
                return False
        except KeyboardInterrupt:
            exit(1)
        except:
            return False

    def brute(self, file, scan_type: ScanType):
        with open(file) as json_in:
            users = json.load(json_in)
        if scan_type == ScanType.DEFAULTS:
            self.default_logins(users)
        elif scan_type == ScanType.LEAKS:
            self.leaked_logins(users)
        else:
            raise NotImplementedError("Only Leaks and Default Passwords are supported by now")
        with open(self.logfile(scan_type), "a") as log:
            for attempt in self.found:
                log.write(attempt + "\n")


