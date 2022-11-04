import re
import secrets
import string
import time
from datetime import tzinfo, timedelta
from pathlib import Path

import requests
import tldextract.tldextract
from colorama import Fore


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def colors(string, color):
    return f"{color}{string}{Fore.WHITE}"


def colored(message, color: Fore, symbol="*", indent=0):
    return " " * indent + colors(f"[{symbol}] ", color) + message


def info(message, indent=0):
    print(colored(message, indent=indent, symbol="*", color=Fore.BLUE), flush=True)


def error(message, indent=0):
    print(colored(message, indent=indent, symbol="-", color=Fore.RED), flush=True)


def fatal(message, indent=0):
    print(colored(message, indent=indent, symbol="-", color=Fore.RED), flush=True)
    exit(1)


def success(message, indent=0):
    print(colored(message, indent=indent, symbol="+", color=Fore.GREEN), flush=True)


def warning(message, indent=0):
    print(colored(message, indent=indent, symbol="#", color=Fore.YELLOW), flush=True)


def debug(message, indent=0):
    print(colored(message, indent=indent, symbol="$", color=Fore.MAGENTA), flush=True)


def progress(message, indent=0):
    print(colored(message, indent=indent, symbol=">", color=Fore.CYAN), flush=True)


def highlight(what):
    return f"{Fore.LIGHTCYAN_EX}{what}{Fore.WHITE}"


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
    return domain.replace(remove, "", 1)


def extract_domain(domain):
    ext = tldextract.tldextract.extract(domain)
    return ext.fqdn


def create_additional_info(domain=None, subdomain=None, endpoint=None):
    return {
        "Domain": domain.additional_info_json if domain else {},
        "Subdomain": subdomain.additional_info_json if subdomain else {},
        "Endpoint": endpoint.additional_info_json if endpoint else {}
    }


def validate_target_port(target):
    valid_port = False
    if not target.find(":"):
        return valid_port
    port = target.split(":")[1]
    if not port:
        return valid_port
    return validate_port(valid_port)


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
