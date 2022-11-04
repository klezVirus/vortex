import configparser
import json
import os
import re
import subprocess
import io
import time
import subprocess
import sys
import traceback
from pydoc import locate
from pathlib import Path

from utils.utils import *


class Amass:
    def __init__(self, domain: str = None):
        self.path = Path("amass")
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(get_project_root().joinpath("config", "config.ini"))
        try:
            if sys.platform.startswith("win"):
                out = subprocess.check_output(f"where {self.path}", shell=True)
            else:
                out = subprocess.check_output(f"which {self.path}", shell=True)
            for line in out.decode().split("\n"):
                if line.find(f"{self.path.name}") > -1:
                    self.path = Path(line.strip())
            if not self.path or not self.path.is_file():
                raise FileNotFoundError
        except (subprocess.CalledProcessError, FileNotFoundError):
            error(f"Amass is not in the PATH. Please install amass and add it to your path.")
            sys.exit(1)
        self.prefix_cmd = None
        self.suffix_cmd = None
        self.__action = ""
        self.__args = {}
        self.__sep = " "
        self.debug = bool(self.config.get("DEBUG", "developer"))
        self.__domain = domain
        self.data_file = get_project_root().joinpath("data", "temp", f"amass-{self.__domain}-{time_label()}")
        self.passive = True
        self.__resolvers = get_project_root().joinpath(self.config.get("SUBDOMAINS", "resolvers")).absolute()
        self.__names = get_project_root().joinpath(self.config.get("SUBDOMAINS", "names")).absolute()

    @property
    def domain(self):
        return self.__domain

    @domain.setter
    def domain(self, value: str):
        self.__domain = value
        self.data_file = get_project_root().joinpath("data", "temp", f"amass-{self.__domain}-{time_label()}")

    def set_passive(self):
        self.__args["-passive"] = None

    def export_to_json(self, file: str):
        file = Path(file).absolute()
        self.__action = "db"
        self.__args["-d"] = self.__domain
        self.__args["-show"] = None
        self.__args["-json"] = f'"{file}"'
        self.__execute()
        self.__args = {}

    def extract_domain_list(self):
        self.__action = "db"
        self.__args["-d"] = self.__domain
        self.__args["-names"] = None
        self.__execute()
        self.__args = {}
        domains = []
        with open(f"{self.data_file}-db.log") as fp:
            for domain in fp.readlines():
                if domain.strip() == "":
                    continue
                domains.append(domain.strip().strip('"'))
        return domains

    def extract_info(self):
        file = get_project_root().joinpath("data", "temp", f"amass-{self.__domain}-data-{time_label()}.json")
        self.export_to_json(str(file))
        json_data = None
        try:
            with open(str(file), "r") as fp:
                json_data = json.load(fp)
        except:
            pass
        if not json_data or "domains" not in json_data.keys():
            return []
        domains = []
        for x in json_data.get("domains"):
            for y in x.get("names"):
                domains.append(y.get("name"))
        return domains

    def enumerate(self):
        self.__action = "enum"
        self.__args["-rf"] = f'"{self.__resolvers}"'
        self.__args["-nf"] = f'"{self.__names}"'
        self.__args["-d"] = self.__domain
        if self.passive:
            self.set_passive()
        self.__execute()
        self.__args = {}

    def __execute(self):
        try:
            args = f"{self.__action} "
            for k in self.__args.keys():
                args += f" {k}{self.__sep}{self.__args[k]}" if self.__args[k] is not None else f" {k}"
            cmd = f"\"{self.path}\" {args}"
            if self.prefix_cmd:
                cmd = f"{self.prefix_cmd} & {cmd}"
            if self.suffix_cmd:
                cmd = f"{cmd} & {self.suffix_cmd}"
            if self.debug:
                print(cmd)

            filename = f"{self.data_file}-{self.__action}.log"
            with io.open(filename, "w") as writer, io.open(filename, "r", 1) as reader:
                process = subprocess.Popen(cmd, stdout=writer, stderr=subprocess.STDOUT)
                while process.poll() is None:
                    sys.stdout.write(reader.read())
                    time.sleep(0.5)
                # Read the remaining
                sys.stdout.write(reader.read())
            return True
        except subprocess.CalledProcessError as e:
            Amass.__check_error_output(e.output.decode(errors="ignore"))
            return False
        except KeyboardInterrupt:
            return False

    @staticmethod
    def __check_error_output(output):
        for line in output.split("\n"):
            if re.search(r"error", line, re.IGNORECASE):
                print(f"  [-] Error: {line}")
            if re.search(r"warning", line, re.IGNORECASE):
                print(f"  [-] Warning: {line}")
        return False

