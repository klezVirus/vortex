import os.path
import traceback

from colorama import Fore

from actions.action import Action
from db.models.domain import Domain
from enumerators.factories import OfficeEnumeratorFactory
from utils.utils import colors, progress, success, info, error, extract_main_domain, fatal, highlight, extract_domain, \
    create_additional_info, is_subdomain, validate_target_port, pretty_print_additional_info


class Office(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.endpoint_types = self.enumerators()
        self.commands = {
            "attack": ["domain", "endpoint_type"],
            "add": ["target", "domain", "endpoint_type"],
            "show": ["domain"],
        }

    def execute(self, **kwargs):
        command = kwargs["command"]
        endpoint_type = kwargs["endpoint_type"]

        if endpoint_type == "all":
            endpoint_type = None

        target = kwargs["domain"]

        use_leaks = kwargs["leaks"]
        passwords_file = kwargs["passwords_file"]
        if not passwords_file and not use_leaks and command == "attack":
            error("A password file should be given or define 'use leaks' (-L, or --leaks) instead")
            exit(1)
        passwords = None
        if passwords_file and os.path.isfile(passwords_file):
            passwords = [p.strip() for p in open(passwords_file).readlines()]

        # This is necessary in office because we need to know if we already
        # Performed any scan against the domain
        main_domain = extract_main_domain(target)
        if not self.dbms.exists_domain(main_domain):
            fatal(
                f"{main_domain} not found in the DB. you should run "
                f"`{highlight(f'python vortex -w {self.dbh.workspace} subdomain -D {main_domain} -c [enum|brute]')}`"
            )

        if command == "show":
            main_domain_object = self.dbms.get_domain(target)
            domain_information = main_domain_object.additional_info_json
            pretty_print_additional_info(domain_information)
            return

        if command == "just-spray":
            main_domain_object = self.dbms.get_domain(target)
            domain_information = main_domain_object.additional_info_json

            return

        # Get all registered subdomains
        subdomains = self.dbms.get_subdomains(target)
        # Get all registered endpoints
        endpoints = self.dbms.get_endpoints(target)
        # Get all registered users
        users = self.dbms.get_users()

        if len(subdomains) == 0 or len(endpoints) == 0:
            fatal(
                f"{target} not found in the DB. Please run the following commands first:"
                f"- 1. Add subdomain: `{highlight(f'python vortex -w {self.dbh.workspace} subdomain -c add {target}')}`"
                f"- 2. Portscan:      `{highlight(f'python vortex -w {self.dbh.workspace} portscan -c single {target}')}`"
            )

        if command == "attack":
            for endpoint in endpoints:
                vpn_name = self.dbms.get_etype_name(endpoint.endpoint_type)
                if endpoint_type and vpn_name != endpoint_type:
                    continue

                subdomain = extract_domain(endpoint.target)
                additional_info = self.dbms.create_additional_info(main_domain, subdomain, endpoint)
                additional_info["aws"] = kwargs["aws"]
                additional_info["action"] = "spray"
                additional_info["dbh"] = self.dbh

                enumerator = OfficeEnumeratorFactory.from_name(vpn_name, endpoint.target)
                if not enumerator:
                    continue
                enumerator.setup(**additional_info)
                info(f"Running {enumerator.__class__.__name__} against {endpoint.target}")
                enumerator.parallel_login(users=users, passwords=passwords, use_leaks=use_leaks)
                self.dbms.save_logins(enumerator.found, endpoint.eid)
                if kwargs.get("aws"):
                    info("AWS Manager: Destroying APIs...")
                    enumerator.aws_manager.clear_all_apis_in_session()

        elif command == "add":
            domain_obj = self.dbms.get_domain(target)
            if not domain_obj:
                domain_obj = Domain(did=0, name=target, email_format=None)

            for etype in self.dbms.db_etypes():
                enumerator = OfficeEnumeratorFactory.from_name(etype.name, target, group="dummy")
                if not enumerator:
                    continue
                enumerator.setup(**domain_obj.additional_info_json)
                if enumerator.validate():
                    success(f"{target} is a valid {etype.name.upper()} target!")
                    if self.dbms.get_endpoint(target, etype.etid):
                        info(f"{target} already in the DB")
                        continue
                    else:
                        self.dbms.add_endpoint(target, etype.etid)
                        success(f"Added {target} to the DB")

                else:
                    error(f"{target} does not seem a valid {etype.name.upper()} target")
