import secrets
import string
import time
from datetime import tzinfo, timedelta
from pathlib import Path

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


def success(message, indent=0):
    print(colored(message, indent=indent, symbol="+", color=Fore.GREEN), flush=True)


def warning(message, indent=0):
    print(colored(message, indent=indent, symbol="#", color=Fore.YELLOW), flush=True)


def debug(message, indent=0):
    print(colored(message, indent=indent, symbol="$", color=Fore.MAGENTA), flush=True)


def progress(message, indent=0):
    print(colored(message, indent=indent, symbol=">", color=Fore.CYAN), flush=True)


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
