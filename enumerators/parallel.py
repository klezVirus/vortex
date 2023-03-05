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
        self.lock = threading.Lock()

    def run(self):
        while True:
            username, password, group = self.threading_object.dequeue()
            if not username or not password:
                return
            try:
                result, res = self.threading_object.safe_login(username, password, group=group)
                msg = f"RESULT: {'SUCCESS' if result else 'FAILED'}; RESPONSE: {pickle.dumps(res) if res else ''}"
                self.threading_object.logger.debug(msg)
                if result:
                    self.threading_object.add_valid_login(username, password)
                    success(f"{username:50}:{password:50}:{self.threading_object.group:20} is valid! -- CODE: {res.status_code} ; LEN: {len(res.text):8}", lock=self.lock)
                else:
                    with threading.Lock():
                        error(f"{username:50}:{password:50}:{self.threading_object.group:20} is not valid. -- CODE: {res.status_code} ; LEN: {len(res.text):8}", lock=self.lock)
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
                endpoint_type_name = self.threading_object.dbms.get_etype_name(endpoint_type_label)
                result, res = enumerator.safe_validate()
                msg = f"RESULT: {'SUCCESS' if result else 'FAILED'}; RESPONSE: {pickle.dumps(res) if res else ''}"

                if result:
                    self.threading_object.add_endpoint(enumerator, endpoint_type_label)
                    if self.threading_object.debug:
                        success(f"{enumerator.target.strip()} is a {endpoint_type_name} endpoint")
                else:
                    if self.threading_object.debug:
                        error(f"{enumerator.target.strip()} is not a {endpoint_type_name} endpoint")
            except KeyboardInterrupt:
                error("Aborted by user")
                multiprocessing.current_process().terminate()
            except Exception as e:
                traceback.print_exc()
                debug(f"Exception: {enumerator.__class__.__name__} - {e}")
            self.threading_object.done()

