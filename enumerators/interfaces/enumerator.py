import configparser
import json
import logging
import queue
import random
import threading
import time
import traceback
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from queue import Empty
from abc import ABC, abstractmethod
from enum import Enum
import sqlite3 as sql
from http.client import RemoteDisconnected
from pydoc import locate
from typing import Union

import requests
from colorama import Fore

from enumerators.interfaces.ignite import Ignite
from enumerators.parallel import Worker
from utils.detectors.nuclei import Nuclei
from utils.notifiers.notify import Notifier
from utils.utils import get_project_root, colors, success, error


class VpnEnumerator(Ignite):
    def __init__(self):
        super().__init__()
        self.nuclei = Nuclei()
        self.info = None
        self.group_field = None
        self.groups = []
        self.realms = []
        self.notifier = Notifier(
            **{
                "slack_webhook": self.config.get("NOTIFICATIONS", "slack_webhook"),
                "discord_webhook": self.config.get("NOTIFICATIONS", "discord_webhook"),
                "teams_webhook": self.config.get("NOTIFICATIONS", "teams_webhook"),
                "pushover_token": self.config.get("NOTIFICATIONS", "pushover_token"),
                "pushover_user": self.config.get("NOTIFICATIONS", "pushover_user"),
                "operator": self.config.get("OPERATION", "operator_id"),
                "exclude_password": self.config.getboolean("NOTIFICATIONS", "exclude_password")
            }
        )

    def setup(self, **kwargs):
        super().setup(**kwargs)
        action = kwargs.pop("action", "detect")

        self.info = kwargs
        groups = kwargs.get("Endpoint", {}).get("nuclei", {}).get("groups", [])
        self.group_field = kwargs.get("Endpoint", {}).get("nuclei", {}).get("group_field", "")
        if groups:
            if isinstance(groups, str):
                groups = groups.split(",")
            elif isinstance(groups, list):
                groups = groups
            self.groups = groups

        if len(self.groups) == 0:
            self.groups = ["N/A"]

        if kwargs.get("aws"):
            self.setup_awsm(self.target, **kwargs)

        kwargs = {
            "action": action,
            "class": self.__class__.__name__,
            "target": self.target,
            "lock": kwargs.get("lock") if "lock" in kwargs.keys() else None
        }
        self.nuclei.setup(**kwargs)

    def add_valid_login(self, username, password, group):
        self.lock.acquire()
        self.found.append({"username": username, "password": password, "group": group})
        self.lock.release()

    def enqueue(self, value):
        self.queue.put(value, block=True, timeout=5)

    def dequeue(self):
        try:
            return self.queue.get(block=True, timeout=1)
        except Empty:
            return None, None

    def done(self):
        try:
            return self.queue.task_done()
        except ValueError:
            return

    def parallel_login(self, users: list, passwords: list = None, use_leaks: bool = False):

        args = []
        for user in users:
            for group in self.groups:
                if use_leaks:
                    for leak in user.leaks:
                        args.append((user.email, leak, group))
                else:
                    for password in passwords:
                        args.append((user.email, password, group))

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            for outcome in executor.map(self.safe_login, args):
                result, res, username, password, group = outcome
                if result:
                    self.add_valid_login(*args)
                    with threading.Lock():
                        self.notifier.notify_success(username=username, password=password, group=group,
                                                     url=self.urls[0])
                        success(
                            f"{username:50}:{password:50}:{group:20} is valid! "
                            f"-- CODE: {res.status_code} ; LEN: {len(res.text):8}",
                            lock=self.lock)
                else:
                    with threading.Lock():
                        error(
                            f"{username:50}:{password:50}:{group:20} is not valid! "
                            f"-- CODE: {res.status_code} ; LEN: {len(res.text):8}",
                            lock=self.lock)

    def parallel_login2(self, users: list, passwords: list = None, use_leaks: bool = False):
        if not use_leaks and (passwords is None or len(passwords) == 0):
            return
        attempts = []
        for i in range(self.threads):  # noqa
            thread = Worker()
            thread.threading_object = self
            thread.daemon = True
            thread.start()
        for user in users:
            for group in self.groups:
                if use_leaks:
                    for leak in user.leaks:
                        if f"{user.email}:{leak}" in attempts:
                            continue
                        attempts.append(f"{user.email}:{leak}")
                        self.enqueue((user.email, leak, group))
                else:
                    for password in passwords:
                        if f"{user.email}:{password}" in attempts:
                            continue
                        attempts.append(f"{user.email}:{password}")
                        self.enqueue((user.email, password, group))
        self.queue.join()

    def safe_validate(self) -> tuple:
        retries = self.retry
        redirects = 0
        while True:
            try:
                time.sleep(self.random_throttle)
                self.on_fire()  # The power of having interfaces
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

    def safe_login(self, username, password=None, group=None) -> tuple:
        if isinstance(username, tuple):
            username, password, group = username
        retries = self.retry
        while retries > 0:
            try:
                """
                # Not necessary, rotation is handled by self.target @prop
                if len(self.urls) > 0:
                    with threading.Lock():
                        self.target = self.urls[0]
                        self.urls.rotate(-1)
                """
                time.sleep(self.random_throttle)
                self.on_fire()  # The power of having interfaces
                return self.login(username, password, group=group)
            except (requests.ReadTimeout, ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects):
                retries -= 1
                pass
        return False, None

    def safe_user_enum(self, username) -> tuple:
        retries = self.retry
        while retries > 0:
            try:
                time.sleep(self.random_throttle)
                self.on_fire()  # The power of having interfaces
                return self.user_enum(username)
            except (requests.ReadTimeout, ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects):
                retries -= 1
                pass
        return False, None

    # Not an abstract method because just a few enumerators will support it
    def user_enum(self, user) -> tuple:
        return False, None

    def validate(self) -> tuple:
        return self.nuclei.run()

    @abstractmethod
    def login(self, username, password, **kwargs) -> tuple:
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

    def select_group(self, group):
        if group:
            self.group = group
        else:
            groups = self.find_groups()
            print("[*] Select a VPN group:")
            choice = -1

            for n, g in enumerate(groups, start=0):
                print(f"{n} : {g}")
            while choice < 0 or choice > len(groups) - 1:
                try:
                    choice = int(input("  $> "))
                except KeyboardInterrupt:
                    exit(1)
                except ValueError:
                    pass
            self.group = groups[choice]

    @abstractmethod
    def find_groups(self):
        pass

