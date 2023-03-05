import configparser
import logging
import os
import queue
import random
import threading
import uuid
from abc import ABC, abstractmethod
from threading import Event
import requests

from enumerators.interfaces.ignite import Ignite
from utils.utils import generate_id, generate_ip, generate_trace_id, get_project_root, get_random_user_agent, logfile, \
    error


class Api(Ignite, ABC):
    def __init__(self, username: str = None, password: str = None):
        super().__init__()
        api_config_file = get_project_root().joinpath(self.config.get("API", "config")).absolute()
        if not api_config_file.is_file() and not (username and password):
            error("No config file found, and no credentials provided")
            exit(1)

        self.api_config = configparser.ConfigParser(allow_no_value=True,
                                                    interpolation=configparser.ExtendedInterpolation())
        self.api_config.read(str(api_config_file))

        try:
            self.username = self.api_config.get(self.__class__.__name__.upper(), "username")
            self.password = self.api_config.get(self.__class__.__name__.upper(), "password")
        except configparser.NoOptionError:
            self.username = None
            self.password = None

        try:
            api_keys = self.api_config.get(self.__class__.__name__.upper(), "api_keys")
            self.api_keys = api_keys.split(",") if api_keys else []
        except configparser.NoOptionError:
            self.api_keys = []
        # -1 means that the api is not limited
        self.api_available_credits = -1
        self.api_total_credits = -1
        self.inner_api = None

    @abstractmethod
    def get_total_credits(self):
        pass

    @abstractmethod
    def get_available_credits(self):
        pass

    @abstractmethod
    def rotate_key(self):
        pass