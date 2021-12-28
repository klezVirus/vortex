import configparser
import os
import queue
import threading
import traceback
from _queue import Empty
from abc import ABC, abstractmethod
from pydoc import locate

from colorama import Fore

from db.handler import DBHandler
from utils.utils import error, get_project_root, colors, info


class Action(ABC):
    def __init__(self, workspace):
        self.dbh = DBHandler(workspace=workspace)
        self.commands = []
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(get_project_root().joinpath("config", "config.ini"))
        self.cli = colors(" $> ", Fore.GREEN)
        self.choice = colors(" [y|n]", Fore.LIGHTCYAN_EX) + self.cli
        self.__queue = queue.Queue()
        self.lock = threading.BoundedSemaphore(value=20)
        self.endpoints = []
        self.debug = False

    def add_endpoint(self, endpoint, endpoint_type):
        self.lock.acquire()
        self.endpoints.append({"endpoint": endpoint, "endpoint_type": endpoint_type})
        self.lock.release()

    def print_queue(self):
        print(self.__queue.queue)

    def enqueue(self, value):
        self.__queue.put(value, block=True, timeout=1)

    def dequeue(self):
        try:
            return self.__queue.get(block=True, timeout=1)
        except Empty:
            return None, None

    def wait_threads(self):
        return self.__queue.join()

    def done(self):
        try:
            return self.__queue.task_done()
        except ValueError:
            return

    def wait_for_input(self):
        _in = None
        while not _in:
            try:
                _in = input(self.cli)
            except KeyboardInterrupt:
                error("Aborted by user")
                exit(1)
            except:
                pass
        return _in

    def wait_for_choice(self):
        _in = "k"
        while not _in.lower() in ["y", "n"]:
            try:
                _in = input(self.choice)
            except KeyboardInterrupt:
                error("Aborted by user")
                exit(1)
            except:
                pass
        return _in.lower() == "y"

    def choose_command(self):
        info("Select a command:")
        return self.choose(self.commands)

    def choose(self, _list):
        choice = -1

        for n, g in enumerate(_list, start=0):
            print(f"{n} : {g}")
        while choice < 0 or choice > len(_list) - 1:
            try:
                choice = int(input(self.cli))
            except KeyboardInterrupt:
                error("Aborted by user")
                exit(1)
            except ValueError:
                pass
        return _list[choice]

    def safe_execute(self, **kwargs):
        if not self.dbh.db_initialised() and "command" in kwargs.keys() and kwargs["command"] != "init":
            error(rf"""Workspace not initialized. Please initialise it using:
    python manage.py -w {kwargs['workspace']} db -c init 
            """)
        else:
            self.execute(**kwargs)

    @abstractmethod
    def execute(self, **kwargs):
        pass

    @staticmethod
    def from_name(name: str):
        try:
            signer_class_string = f"actions.{name.lower()}.{name.capitalize()}"
            signer_class = locate(signer_class_string)
            return signer_class
        except:
            traceback.print_exc()
            return None

    @staticmethod
    def list_all():
        path = str(get_project_root().joinpath("actions").absolute())
        actions = [
            f.replace(".py", "") for f in os.listdir(path) if
            os.path.isfile(os.path.join(path, f))
            and f not in [
                "__init__.py",
                "action.py"
            ]
        ]
        return actions
