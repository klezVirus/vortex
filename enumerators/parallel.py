import json
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
                self.threading_object.logger.debug(json.dumps(res))
                if result:
                    self.threading_object.add_valid_login(username, password)
                    success(f"{username:50}:{password:50} is valid! -- CODE: {res.status_code} ; LEN: {len(res.text):8}", indent=2)
                else:
                    error(f"{username:50}:{password:50} is not valid. -- CODE: {res.status_code} ; LEN: {len(res.text):8}", indent=2)
            except Exception as e:
                debug(f"Exception: {e}")
            self.threading_object.done()


class DetectWorker(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.threading_object = None

    def run(self):
        while True:
            enumerator, vpn = self.threading_object.dequeue()
            if enumerator is None:
                continue
            try:
                vpn_name = EndpointType.get_name(vpn)
                if enumerator.safe_validate():
                    self.threading_object.add_endpoint(enumerator.target, vpn)
                    if self.threading_object.debug:
                        success(f"{enumerator.target.strip()} is a {vpn_name} endpoint", indent=2)
                else:
                    if self.threading_object.debug:
                        error(f"{enumerator.target.strip()} is not a {vpn_name} endpoint", indent=2)
            except Exception as e:
                traceback.print_exc()
                debug(f"Exception: {e}")
            self.threading_object.done()
