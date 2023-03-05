import configparser
import time
import traceback
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from pydoc import locate
from queue import Empty

import requests

from enumerators.interfaces.ignite import Ignite
from utils.utils import success, error


class Validator(Ignite):
    def __init__(self):
        super().__init__()
        self.session.max_redirects = 5
        self.domain = None

    def add_valid_user(self, username):
        self.add_found({"username": username})

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

    def parallel_validate(self, users: list):
        with ThreadPoolExecutor(self.threads) as executor:
            for result in executor.map(self.safe_validate, users):
                if result[0]:
                    with self.lock:
                        success(f"Found valid user: {result[1]}")
                    self.add_valid_user(result[1])
                else:
                    with self.lock:
                        error(f"Invalid user: {result[1]}")

    def safe_validate(self, email) -> tuple:
        retries = self.retry
        while retries > 0:
            try:
                time.sleep(self.random_throttle)
                self.on_fire()  # The power of having interfaces
                return self.execute(email=email)
            except (requests.ReadTimeout, ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects):
                retries -= 1
                pass
        return False, None

    def setup(self, **kwargs):
        if kwargs.get("aws"):
            self.setup_awsm(self.target, **kwargs)

    @abstractmethod
    def execute(self, email) -> tuple:
        pass

    @staticmethod
    def from_name(name: str):
        try:
            validator_class_string = f"validators.{name.lower()}.{name}"
            validator_class = locate(validator_class_string)
            return validator_class()
        except:
            traceback.print_exc()
            pass
