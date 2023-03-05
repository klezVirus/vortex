import ipaddress
import random
import re
import secrets
import string
import threading
import time
from datetime import tzinfo, timedelta, datetime
from pathlib import Path
from typing import Union

import requests
import tldextract.tldextract
from bs4 import BeautifulSoup
from colorama import Fore
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from tabulate import tabulate

from utils.mashers.namemash import NameMasher

LINE_FEED = '\n'
CARRIAGE_RETURN = '\r'


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def colors(string, color):
    return f"{color}{string}{Fore.WHITE}"


def colored(message, color: Fore, symbol="*", indent=0):
    return " " * indent + colors(f"[{symbol}] ", color) + message


def thread_safe_print(message, flush=False, lock=None):
    if not lock:
        lock = threading.Lock()
    with lock:
        print(message, flush=flush)


def info(message, indent=0, lock=None):
    thread_safe_print(colored(message, indent=indent, symbol="*", color=Fore.BLUE), flush=True, lock=lock)


def error(message, indent=0, lock=None):
    thread_safe_print(colored(message, indent=indent, symbol="-", color=Fore.RED), flush=True, lock=lock)


def fatal(message, indent=0, lock=None):
    thread_safe_print(colored(message, indent=indent, symbol="-", color=Fore.RED), flush=True, lock=lock)
    exit(1)


def success(message, indent=0, lock=None):
    thread_safe_print(colored(message, indent=indent, symbol="+", color=Fore.GREEN), flush=True, lock=lock)


def warning(message, indent=0, lock=None):
    thread_safe_print(colored(message, indent=indent, symbol="#", color=Fore.YELLOW), flush=True, lock=lock)


def debug(message, indent=0, lock=None):
    thread_safe_print(colored(message, indent=indent, symbol="$", color=Fore.MAGENTA), flush=True, lock=lock)


def progress(message, indent=0, lock=None):
    thread_safe_print(colored(message, indent=indent, symbol=">", color=Fore.CYAN), flush=True, lock=lock)


def highlight(what, color=Fore.LIGHTCYAN_EX):
    return f"{color}{what}{Fore.WHITE}"


def time_label():
    return time.strftime('%Y%m%d%H%M%S')


def logfile(fmt: str, script: str):
    return fmt.replace(
        "#date#", time_label()
    ).replace(
        "#enumerator#", script
    )


def random_ascii_string(size=20):
    return ''.join(secrets.choice(string.ascii_letters) for _ in range(size))


class SimpleUTC(tzinfo):
    def tzname(self, **kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def choose(choices: [list, dict], return_index=False):
    choice = -1
    if isinstance(choices, list):
        for i, element in enumerate(choices, start=1):
            print(f"  {i} - {element}")
        while not 1 <= choice <= len(choices):
            try:
                choice = int(input("  $> ").strip())
            except ValueError:
                continue
            except KeyboardInterrupt:
                error("Aborted by user")
                exit(1)
        if not return_index:
            return choices[choice - 1]
        else:
            return choice - 1
    elif isinstance(choices, dict):
        for i, element in choices.items():
            print(f"  {i} - {element}")
        while choice not in choices.keys():
            try:
                choice = input("  $> ").strip()
            except ValueError:
                continue
            except KeyboardInterrupt:
                error("Aborted by user")
                exit(1)
        if return_index:
            return choice
        else:
            return choices[choice]


def res_to_json(response: requests.Response) -> dict:
    try:
        return response.json()
    except:
        return dict()


def is_subdomain(domain):
    return tldextract.tldextract.extract(domain).subdomain != ""


def extract_main_domain(domain):
    remove = tldextract.tldextract.extract(domain).subdomain + "."
    if remove == ".":
        return domain
    return domain.replace(remove, "", 1)


def extract_domain(domain):
    if not domain:
        return None
    ext = tldextract.tldextract.extract(domain)
    return ext.fqdn


def create_additional_info(domain=None, subdomain=None, endpoint=None):
    return {
        "Domain": domain.additional_info_json if domain else {},
        "Subdomain": subdomain.additional_info_json if subdomain else {},
        "Endpoint": endpoint.additional_info_json if endpoint else {}
    }


def is_url(url):
    return re.match(r"^(http|https)://", url)


def validate_target_port(target):
    scheme = None
    port = None
    if is_url(target):
        scheme, target = target.lower().split("://")
    valid_port = False
    if target.find(":") == -1:
        return valid_port

    tokens = target.split(":")
    if len(tokens) >= 2:
        port = tokens[1]
    if not port and not scheme:
        return valid_port
    if not port and scheme == "https":
        valid_port = 443
    if not port and scheme == "http":
        valid_port = 80
    return validate_port(valid_port)


def extract_target_port(target):
    scheme = None
    port = None
    if is_url(target):
        scheme, target = target.lower().split("://")
    if target.find(":") == -1:
        return target, None

    tokens = target.split(":")
    if len(tokens) >= 2:
        target = tokens[0]
        port = tokens[1]
    if not port and not scheme:
        return target, None
    if not port and scheme == "https":
        port = 443
    if not port and scheme == "http":
        port = 80
    if validate_port(port):
        return target, port
    return target, None


def validate_port(port):
    try:
        port = int(port)
        return 20 < port < 65535
    except ValueError:
        pass
    return False


def wait_for_choice(message=None):
    choice = None
    while not (choice and choice in ['y', 'n']):
        if message:
            info(message)
        try:
            choice = input("[y|n] $> ")
        except (KeyboardInterrupt, EOFError):
            fatal("Aborted by user")
    return choice and choice.lower() == "y"


def wait_for_input_like(regex=".*"):
    value = ""
    pattern = re.compile(f"^{regex}$")
    while not (value and pattern.search(value)):
        try:
            value = input(" $> ")
        except (KeyboardInterrupt, EOFError):
            fatal("Aborted by user")
    return value


def wait_for_input():
    value = None
    while not value:
        try:
            value = input(" $> ")
        except (KeyboardInterrupt, EOFError):
            fatal("Aborted by user")
    return value


def get_random_user_agent():
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)

    return user_agent_rotator.get_random_user_agent()

def get_mobile_user_agent():
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=1, mobile=True)

    return user_agent_rotator.get_random_user_agent()


def generate_ip():
    ip = "127.0.0.1"
    while ipaddress.ip_address(ip).is_private:
        ip = ".".join([str(random.randint(0, 255)) for _ in range(4)])
    return ip


def generate_id():
    return "".join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(10))


def generate_trace_id():
    trace_prefix = "Root=1-"
    first = "".join(random.choice("0123456789abcdef") for _ in range(8))
    second = "".join(random.choice("0123456789abcdef") for _ in range(24))
    return trace_prefix + first + "-" + second


def generate_string(chars):
    return "".join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(chars))


def std_soup(res: Union[requests.Response, str]):
    if isinstance(res, requests.Response):
        res = res.text
    return BeautifulSoup(res, features="html.parser")


def generate_utc_times():
    return [
        datetime.utcnow().replace(tzinfo=SimpleUTC()).isoformat(),
        (datetime.utcnow() + timedelta(days=1)).replace(tzinfo=SimpleUTC()).isoformat()
    ]


def listify(obj: str):
    # Listify the domain
    if obj.find(",") > -1:
        obj = obj.split(",")
    else:
        obj = [obj]
    return obj


def reformat_users(users: list, email_format: str):
    masher = NameMasher()
    masher.fmt = email_format

    for u in users:
        if not u.name or u.name.strip() == "":
            continue
        tokens = u.name.split(" ")
        if len(tokens) == 1:
            continue
        elif len(tokens) == 2:
            u.mail = masher.mash(tokens[0], tokens[1]) + "@" + u.email.split("@")[-1]
        else:
            u.mail = masher.mash(tokens[0], tokens[-1], second_name=tokens[1]) + "@" + u.email.split("@")[-1]
    return users


def pretty_print_dns_info(dns_info):
    table = []
    for record in dns_info:
        table.append([record["name"], record["type"], record["data"]])
    print(tabulate(table, headers=["Name", "Type", "Data"], tablefmt="fancy_grid"))
    table = []


def pretty_print_additional_info(domain_info):
    table = []
    user_realm = domain_info.get("Microsoft", {}).get("UserRealm")
    if user_realm:
        table.append([user_realm.get("DomainName", ""), user_realm.get("FederationBrandName", ""), user_realm.get("NameSpaceType", "")])
    print(tabulate(table, headers=["Domain", "Company", "Type"], tablefmt="fancy_grid"))
    table = []

