import argparse
import configparser
import os

import requests
from colorama import Fore
from urllib3.exceptions import InsecureRequestWarning

from actions.action import Action
from utils.utils import get_project_root, colors, error


class Manager:
    def __init__(self):
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(get_project_root().joinpath("config", "config.ini"))

    def run(self, _action, _workspace, **kwargs):
        kwargs["config"] = get_project_root().joinpath("config", "zzz_doosan/config.ini")
        action_class = Action.from_name(_action)
        if not action_class:
            error(f"Unknown action: {_action}")
        else:
            action_instance = action_class(_workspace)
            action_instance.safe_execute(**kwargs)


def sanitize_workspace(workspace):
    workspace = workspace.replace(".", "_")
    workspace = workspace.replace("\\", "")
    workspace = workspace.replace("/", "")
    return workspace


def print_logo():
    print(rf"""
   ,d#####F^      ,yy############yy       ^9#######,
  ,######"      y###################by      ^9######,
  ######^     y#####F""       ^"9######y      "######]
 d#####^    ,#####" {colors("by klezVirus", Fore.BLUE)} ^9#####,     ^######,
,#####]    ,####F    yy#######y,    ^9####b     ^######
[#####     ####F   ,###F""'"9####,    9####]     9#####
#####F    [####   ,##F^  yy   "###b    9####,    ^#####]
#####]    [###]   ###  dF""#b  ^###]   ^####]     #####]
9####b    [####   9##, 9bd [#]  [##b    #####     [#####
[#####     ####,   9##y, ,y##^  d##F    #####     [####]
 #####b    ^####y   ^"#####"   d###^   ,####]     d#####
 [#####,    ^####by          ,d###^    d####^     #####F
  9#####y     "#####byyyyyyd####F^    d####F     [#####9
   9#####b,     ""############"^    ,d####F     ,######
    ^######b,       ""'""'"^      ,d#####F      d#####F
    """)


if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    os.system('color')
    print_logo()
    parser = argparse.ArgumentParser(description="Vortex: VPN Overall Reconnaissance, Enumeration and eXploitation")

    # Required args
    parser.add_argument("action", choices=Action.list_all(),
                        help="Action to execute")
    parser.add_argument("-w", "--workspace", required=True, default=None,
                        help="Workspace to use")

    # Shared args
    parser.add_argument("-c", "--command", required=False, default=None,
                        help="Command for the action")

    # Search operation
    parser.add_argument("-D", "--domain", required=False, default=None,
                        help="Domain under attack")
    parser.add_argument("-C", "--company", required=False, default=None,
                        help="Company under attack")
    parser.add_argument("-l", "--location", required=False, default=None,
                        help="Location of the company under attack (IE, UK, US, ...)")

    # DB operations
    # 1. Add Endpoint
    parser.add_argument("-u", "--url", required=False, default=None,
                        help="VPN Endpoint Origin (schema://domain:port)")
    parser.add_argument("-t", "--endpoint-type", required=False, default=None,
                        help="Target Endpoint Type")
    # 2. Add User
    parser.add_argument("-U", "--user", required=False, default=None,
                        help="User name")
    parser.add_argument("-E", "--email", required=False, default=None,
                        help="User email")
    parser.add_argument("-N", "--name", required=False, default=None,
                        help="User full name")
    parser.add_argument("-R", "--role", required=False, default=None,
                        help="User job")
    # 3. Execute SQL
    parser.add_argument("-s", "--sql", required=False, default=None,
                        help="SQL statement")
    # 4. Export
    parser.add_argument("-O", "--export-file", required=False, default=None,
                        help="Export file")
    parser.add_argument("-Q", "--quotes", required=False, default=None,
                        help="Produce an Excel safe CSV")
    parser.add_argument("-nh", "--no-headers", required=False, action="store_true",
                        help="Remove CSV headers")

    # Profile operation
    parser.add_argument("-k", "--keywords", required=False, default=[], action='append',
                        help="Search keywords")

    # VPN operation
    parser.add_argument("-P", "--passwords-file", required=False, default=None,
                        help="Password file for spraying")
    parser.add_argument("-L", "--leaks", required=False, action="store_true",
                        help="Use leaks for spraying")

    # Import operation
    parser.add_argument("-I", "--import-file", required=False, default=None,
                        help="Import file")

    args = parser.parse_args()

    args.workspace = sanitize_workspace(args.workspace)

    manager = Manager()
    dictionary_args = vars(args)
    try:
        manager.run(args.action, args.workspace, **dictionary_args)
    except KeyboardInterrupt:
        error("Aborted by user")


