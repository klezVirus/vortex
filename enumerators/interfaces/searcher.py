import configparser
import json
import logging
import queue
import random
import threading
import time
import traceback
from typing import Union

from _queue import Empty
from abc import ABC, abstractmethod
from http.client import RemoteDisconnected
from pydoc import locate

import requests

from db.dao.leak import LeakDao
from db.dao.user import UserDao
from enumerators.interfaces.ignite import Ignite
from enumerators.search.structures.unified_user_data import UnifiedUserDataList, UnifiedUserData


class Searcher(Ignite):
    def __init__(self):
        super().__init__()
        self.results = 0
        self.accounts = None
        self.filter = None
        self.uu_data = UnifiedUserDataList()
        self.__retry = 3

    def add_filter(self, f):
        self.filter = f

    @abstractmethod
    def setup(self, **kwargs):
        pass

    @abstractmethod
    def search(self) -> tuple:
        pass

    def add_user_info(self, name="", email="", password="", location="", text="", phone="", username="", role="", address="", phash="", db=""):
        self.lock.acquire()
        self.uu_data.append(
            UnifiedUserData(
                name=name,
                email=email,
                password=password,
                location=location,
                text=text,
                phone=phone,
                username=username,
                role=role,
                address=address,
                phash=phash,
                db=db
            )
        )
        self.results += 1
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

    def parallel_search(self):
        pass

    def safe_search(self) -> tuple:
        retries = self.__retry
        redirects = 0
        while True:
            try:
                time.sleep(self.random_throttle)
                self.on_fire()  # The power of having interfaces
                return self.search()
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

    @staticmethod
    def from_name(name: str):
        try:
            enumerator_class_string = f"enumerators.search.{name}.{name.capitalize()}Enumerator"
            print(enumerator_class_string)
            enumerator_class = locate(enumerator_class_string)
            return enumerator_class
        except:
            traceback.print_exc()
            pass

