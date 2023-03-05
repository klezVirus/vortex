import configparser
import os
from pathlib import Path

import psutil

from actions.action import Action
import subprocess

from utils.managers.aws import AWSManager
from utils.utils import get_project_root, info, debug, error


class Aws(Action):
    def __init__(self, workspace=None):
        super().__init__(workspace)
        self.commands = {"list": [], "clear": [], "delete": ["filter"], "clear-region": ["filter"], "sync": []}
        kwargs = {"dbh": self.dbh}
        self.awsm = AWSManager(**kwargs)
        self.no_child_process = True

    def execute(self, **kwargs):
        command = kwargs["command"]
        if command == "list":
            info(f"Listing all FireProx APIs...")
            if kwargs.get("online"):
                self.awsm.list_apis()
            else:
                self.awsm.list_apis_offline()
        elif command == "clear":
            info(f"Checking API status...")
            self.awsm.list_apis()
            info(f"Deleting all APIs...")
            self.awsm.clear_all_apis()
        elif command == "clear-region":
            _filter = kwargs["filter"]
            if _filter not in self.awsm.regions:
                error(f"Region {_filter} is invalid")
                return
            info(f"Deleting all APIs in {_filter}...")
            self.awsm.destroy_in_region(_filter)
        elif command == "delete":
            _filter = kwargs["filter"]
            info(f"Deleting API ID: {_filter}")
            self.awsm.fp_rm_api(_filter)
        elif command == "sync":
            error("Not implemented yet")
        else:
            return
