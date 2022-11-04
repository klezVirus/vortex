import json
import multiprocessing
import os
import pickle
import threading
import time
import traceback

from colorama import Fore

from db.enums.types import EndpointType
from utils.utils import colors, success, error, debug


class Worker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.threading_object = None

    def run(self):
        while True:
            username, password = self.threading_object.dequeue()
            if not username or not password:
                return
            try:
                result, res = self.threading_object.safe_login(username, password)
                msg = f"RESULT: {'SUCCESS' if result else 'FAILED'}; RESPONSE: {pickle.dumps(res) if res else ''}"
                self.threading_object.logger.debug(msg)
                if result:
                    self.threading_object.add_valid_login(username, password)
                    success(f"{username:50}:{password:50} is valid! -- CODE: {res.status_code} ; LEN: {len(res.text):8}", indent=2)
                else:
                    error(f"{username:50}:{password:50} is not valid. -- CODE: {res.status_code} ; LEN: {len(res.text):8}", indent=2)
            except KeyboardInterrupt:
                error("Aborted by user")
                multiprocessing.current_process().terminate()
            except Exception as e:
                debug(f"Exception: {e}")
            self.threading_object.done()


class DetectWorker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.threading_object = None

    def run(self):
        while True:
            enumerator, endpoint_type_label = self.threading_object.dequeue()
            if enumerator is None:
                continue
            try:
                endpoint_type_name = EndpointType.get_name(endpoint_type_label)
                result, res = enumerator.safe_validate()
                msg = f"RESULT: {'SUCCESS' if result else 'FAILED'}; RESPONSE: {pickle.dumps(res) if res else ''}"
                if result:
                    self.threading_object.add_endpoint(enumerator, endpoint_type_label)
                    if self.threading_object.debug:
                        success(f"{enumerator.target.strip()} is a {endpoint_type_name} endpoint", indent=2)
                else:
                    self.threading_object.add_endpoint(enumerator, EndpointType.UNKNOWN.value)
                    if self.threading_object.debug:
                        error(f"{enumerator.target.strip()} is not a {endpoint_type_name} endpoint", indent=2)
            except KeyboardInterrupt:
                error("Aborted by user")
                multiprocessing.current_process().terminate()
            except Exception as e:
                # traceback.print_exc()
                debug(f"Exception: {enumerator.__class__.__name__} - {e}")
            self.threading_object.done()


class UserEnumWorker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.threading_object = None

    def run(self):
        # Worker to use when an endpoint allows for user enumeration
        # TODO: The code below is WRONG. Fix it

        while True:
            enumerator, endpoint_type_label = self.threading_object.dequeue()
            if enumerator is None:
                continue
            try:
                endpoint_type_name = EndpointType.get_name(endpoint_type_label)
                result, res = enumerator.safe_validate()
                msg = f"RESULT: {'SUCCESS' if result else 'FAILED'}; RESPONSE: {pickle.dumps(res) if res else ''}"
                if result:
                    self.threading_object.add_endpoint(enumerator.target, endpoint_type_label)
                    if self.threading_object.debug:
                        success(f"{enumerator.target.strip()} is a {endpoint_type_name} endpoint", indent=2)
                else:
                    if self.threading_object.debug:
                        error(f"{enumerator.target.strip()} is not a {endpoint_type_name} endpoint", indent=2)
            except Exception as e:
                traceback.print_exc()
                debug(f"Exception: {e}")
            self.threading_object.done()


class ValidateWorker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.threading_object = None

    def run(self):
        # To refactor, we would like parallel validation for users and endpoints
        # TODO: The code below is WRONG. Fix it

        while True:
            session, url = self.threading_object.dequeue()
            enumerator, endpoint_type_label = self.threading_object.dequeue()

            if enumerator is None:
                continue
            try:
                endpoint_type_name = EndpointType.get_name(endpoint_type_label)
                result, res = enumerator.safe_validate()
                msg = f"RESULT: {'SUCCESS' if result else 'FAILED'}; RESPONSE: {pickle.dumps(res) if res else ''}"
                if result:
                    self.threading_object.add_endpoint(enumerator.target, endpoint_type_label)
                    if self.threading_object.debug:
                        success(f"{enumerator.target.strip()} is a {endpoint_type_name} endpoint", indent=2)
                else:
                    if self.threading_object.debug:
                        error(f"{enumerator.target.strip()} is not a {endpoint_type_name} endpoint", indent=2)
            except Exception as e:
                traceback.print_exc()
                debug(f"Exception: {e}")
            self.threading_object.done()
