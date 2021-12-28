import secrets
import string
import time
from datetime import tzinfo, timedelta
from pathlib import Path

from colorama import Fore


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def colors(string, color):
    """Make things colorfull

    Arguments:
        string {str} -- String to apply colors on
        color {int} -- value of color to apply

    """
    return f"{color}{string}{Fore.WHITE}"


def colored(message, color: Fore, symbol="*", indent=0):
    return " " * indent + colors(f"[{symbol}] ", color) + message


def info(message, indent=0):
    print(colored(message, indent=indent, symbol="*", color=Fore.BLUE))


def error(message, indent=0):
    print(colored(message, indent=indent, symbol="-", color=Fore.RED))


def success(message, indent=0):
    print(colored(message, indent=indent, symbol="+", color=Fore.GREEN))


def warning(message, indent=0):
    print(colored(message, indent=indent, symbol="#", color=Fore.YELLOW))


def debug(message, indent=0):
    print(colored(message, indent=indent, symbol="$", color=Fore.MAGENTA))


def progress(message, indent=0):
    print(colored(message, indent=indent, symbol=">", color=Fore.CYAN))


def time_label():
    return time.strftime('%Y%m%d%H%M%S')


def logfile(fmt: str, script: str, scan_type: str):
    return fmt.replace(
        "#scan#", scan_type
    ).replace(
        "#date#", time_label()
    ).replace(
        "#script#", script
    )


def random_ascii_string(size=20):
    return ''.join(secrets.choice(string.ascii_letters) for _ in range(size))


class SimpleUTC(tzinfo):
    def tzname(self, **kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)
