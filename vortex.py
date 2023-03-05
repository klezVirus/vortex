import argparse
import configparser
import os
from multiprocessing import Process

import requests
from colorama import Fore
from urllib3.exceptions import InsecureRequestWarning

from actions.action import Action
from utils.utils import get_project_root, colors, error, fatal, info, wait_for_input, choose


class Manager:
    def __init__(self):
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(get_project_root().joinpath("config", "config.ini"))
        workspaces = get_project_root().joinpath("data", "workspaces")
        temp = get_project_root().joinpath("data", "temp")
        workspaces.mkdir(exist_ok=True)
        temp.mkdir(exist_ok=True)
        self.action_instance = None
        self.action_vargs = None

    def setup(self, _action, _workspace, dictionary):

        dictionary["config"] = get_project_root().joinpath("config", "config.ini")
        action_class = Action.from_name(_action)
        if not action_class:
            fatal(f"Unknown action: {_action}")
            return
        action_instance = action_class(_workspace)
        c = dictionary.get("command")
        while c is None or c not in action_instance.commands.keys():
            info(f"Please enter a command")
            c = choose(list(action_instance.commands.keys()))

        dictionary["command"] = c
        for k, v in dictionary.items():
            if k in action_instance.commands.get(c) and v is None:
                error(f"{k} field is required")
                info(f"Please enter a value for {k}")
                if k == "endpoint_type":
                    dictionary[k] = choose(action_instance.endpoint_types + ["all"])
                elif k == "tool":
                    dictionary[k] = choose(["Amass", "Sublist3r"])
                else:
                    dictionary[k] = wait_for_input()
        if "email_format" in action_instance.commands.get(c):
            from utils.mashers.namemash import NameMasher
            from db.dao.domain import DomainDao
            domain = dictionary.get("domain")
            masher = NameMasher()
            d_dao = DomainDao(action_instance.dbh)
            mail_format = d_dao.get_email_format(domain)
            if not mail_format:
                mail_format = action_instance.dbh.get_email_format()
            if not mail_format:
                mail_format = masher.select_format()
            dictionary["email_format"] = mail_format
            if not mail_format:
                fatal("An email format is needed to continue")
            if not d_dao.update_email_format(domain, email_format=mail_format):
                action_instance.dbh.set_email_format(mail_format)

        self.action_vargs = dictionary
        return not action_instance.no_child_process

    def run(self, _action, _workspace):
        action_class = Action.from_name(_action)
        if not action_class:
            error(f"Unknown action: {_action}")
        else:
            action_instance = action_class(_workspace)
            action_instance.safe_execute(**self.action_vargs)


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
    if os.name == 'nt':
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

    # Subdomain operation
    parser.add_argument("--resolve", required=False, default=None, action="store_true",
                        help="Add Domain resolution to subdomain enumeration")
    parser.add_argument("--takeover", required=False, default=None, action="store_true",
                        help="Check for subdomains which can be taken over")
    parser.add_argument("--tool", required=False, default="Amass", choices=["Amass", "Sublist3r"],
                        help="External tool for subdomain enumeration")

    # Search operation
    parser.add_argument("-D", "--domain", required=False, default=None,
                        help="Domain under attack")
    parser.add_argument("-f", "--filter", required=False, default=None,
                        help="Regex filter to use to filter out domain/targets")
    parser.add_argument("-C", "--company", required=False, default=None,
                        help="Company under attack")
    parser.add_argument("-l", "--location", required=False, default=None,
                        help="Location of the company under attack (IE, UK, US, ...)")
    parser.add_argument("-cc", "--current-company", required=False, default=None, type=int,
                        help="Universal Resource Number (urn) of the current company")
    parser.add_argument("-T", "--title", required=False, default=None,
                        help="Filter based on employee role (Engineer, Manager, ...)")
    parser.add_argument("--otp", required=False, default=None,
                        help="OTP code for LinkedIn Login")

    # DB operations
    # 1. Add Endpoint
    parser.add_argument("-u", "--url", required=False, default=None,
                        help="VPN Endpoint Origin (schema://domain:port)")
    parser.add_argument("-t", "--endpoint-type", required=False, default=None,
                        help="Target Endpoint Type")
    parser.add_argument("--no-validate", required=False, default=None, action="store_true",
                        help="Skip validation during Port Scan")
    parser.add_argument("--ports", required=False, default=None, type=str,
                        help="Comma separated list of ports to scan (Override config)")
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

    # Validation operation
    parser.add_argument("--tech", required=False, default="O365Enum", choices=["O365Enum", "O365Creeper", "Onedrive"],
                        help="External tool for subdomain enumeration")

    # Setup notifiers
    parser.add_argument("--notify", required=False, default="all", choices=["discord", "slack", "teams", "all"],
                        help="Notify about successful operations using the specified channel")

    # Setup AWS
    parser.add_argument("--aws", required=False, action="store_true", default=False,
                        help="Using AWS APIs to generate random IPs and bypass rate limiting")
    # Check AWS API online
    parser.add_argument("--online", required=False, action="store_true", default=False,
                        help="When used with aws -c list, will check AWS API directly online")

    args = parser.parse_args()

    args.workspace = sanitize_workspace(args.workspace)

    manager = Manager()
    dictionary_args = vars(args)
    use_child_process = manager.setup(args.action, args.workspace, dictionary_args)
    if use_child_process:
        process = None
        try:
            process = Process(target=manager.run, args=(args.action, args.workspace))
            process.start()
            process.join()
        except KeyboardInterrupt:
            error("Aborted by user")
            if process and process.is_alive():
                process.terminate()
    else:
        manager.run(args.action, args.workspace)
