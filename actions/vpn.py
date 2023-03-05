import os.path

from actions.action import Action
from enumerators.factories import VpnEnumeratorFactory
from utils.utils import success, info, progress, error, is_subdomain, fatal, highlight, reformat_users


class Vpn(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.endpoint_types = self.enumerators()
        self.commands = {
            "attack": ["url", "endpoint_type"],
            "add": ["url", "endpoint_type"]
        }

    def execute(self, **kwargs):
        self.dbh.connect()
        command = kwargs["command"]
        email_format = kwargs.get("email_format", None)

        use_leaks = kwargs["leaks"]
        passwords_file = kwargs["passwords_file"]
        if not passwords_file and not use_leaks and command == "attack":
            error("A password file should be given or define 'use leaks' (-L, or --leaks) instead")
            exit(1)

        endpoint_type = kwargs["endpoint_type"]

        if endpoint_type == "all":
            endpoint_type = None

        # Get all registered users
        users = self.dbms.db_users()

        if email_format:
            info(f"Custom email format selected: {email_format}")
            users = reformat_users(users, email_format)

        passwords = None
        if passwords_file and os.path.isfile(passwords_file):
            passwords = [p.strip() for p in open(passwords_file).readlines()]

        target = kwargs["url"]
        if target is None:
            error("URL field is required!")
            info("If you're adding a domain, then insert the correct VPN target (IP:PORT)")
            info("Otherwise, you can enter any filter to restrict the attack")
            info("Example: -D example -> Will attack all endpoints like %example%")
            info("Example: -D vpn.example.com:443 -> Will attack only vpn.example.com")
            return

        target = target.strip()
        endpoints = self.dbms.get_endpoints(target)

        if len(endpoints) == 0:
            fatal(
                f"{target} not found in the DB. Please run the following commands first:\n"
                f"\t- 1. Add subdomain: `{highlight(f'python vortex -w {self.dbh.workspace} subdomain -c add {target}')}`\n"
                f"\t- 2. Portscan:      `{highlight(f'python vortex -w {self.dbh.workspace} portscan -c single {target}')}`\n"
            )

        if command == "attack":
            for endpoint in endpoints:
                if self.dbms.get_etype_name(endpoint.etype_ref).lower() not in self.endpoint_types:
                    continue
                info(f"Attacking {endpoint.target}")
                additional_info = self.dbms.create_additional_info(endpoint=endpoint)
                additional_info["aws"] = kwargs["aws"]
                additional_info["action"] = "spray"
                additional_info["dbh"] = self.dbh

                vpn_name = self.dbms.get_etype_name(endpoint.etype_ref)

                enumerator = VpnEnumeratorFactory.from_name(vpn_name, endpoint.target)
                if not enumerator:
                    error("Not a VPN endpoint, skipping.")
                    continue
                enumerator.setup(**additional_info)

                enumerator.parallel_login(users=users, passwords=passwords, use_leaks=use_leaks)
                progress(f"Found {len(enumerator.found)} valid logins")
                info("Updating Db...")
                self.dbms.update_logins(enumerator.found, endpoint.eid)
                if kwargs.get("aws"):
                    info("AWS Manager: Destroying APIs...")
                    enumerator.aws_manager.clear_all_apis_in_session()
                success("Done")

        elif command == "add":
            if not is_subdomain(target):
                fatal("Domain should be a subdomain")

            vpn = kwargs["endpoint_type"]
            endpoint_type = None
            if vpn is None:
                for etype in self.dbms.db_etypes():
                    enumerator = VpnEnumeratorFactory.from_name(etype.name, target, group="dummy")
                    if enumerator is None:
                        continue
                    result, res = enumerator.safe_validate()
                    if result:
                        success(f"{target} is a {etype.name} target!")
                        endpoint_type = etype.etid
                        break
                    else:
                        error(f"{target} is not a {etype.name} target.")

            else:
                endpoint_type = self.dbms.get_etype_id(vpn)

            if endpoint_type is None and vpn is not None:
                print(f"[-] {vpn} is not a valid VPN type")
                exit(1)
            elif endpoint_type is None:
                print(f"[-] Cannot add target: unknown VPN type")
                exit(1)

            if not self.dbms.find_endpoint(target, endpoint_type):
                self.dbms.add_endpoint(target, endpoint_type)
                success(f"Added {target} to the DB")


