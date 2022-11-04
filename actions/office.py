import os.path
import traceback

from colorama import Fore

from actions.action import Action
from db.dao.domain import DomainDao
from db.dao.endpoint import EndpointDao
from db.dao.login import LoginDao
from db.dao.user import UserDao
from db.enums.types import EndpointType
from db.models.domain import Domain
from db.models.endpoint import Endpoint
from enumerators.factories import OfficeEnumeratorFactory
from utils.utils import colors, progress, success, info, error, extract_main_domain, fatal, highlight, extract_domain, \
    create_additional_info, is_subdomain, validate_target_port


class Office(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.endpoint_types = ["owa", "lync", "imap", "adfs", "o365"]
        self.commands = ["attack", "add"]

    def execute(self, **kwargs):
        self.dbh.connect()
        u_dao = UserDao(handler=self.dbh)
        e_dao = EndpointDao(handler=self.dbh)
        d_dao = DomainDao(handler=self.dbh)
        s_dao = LoginDao(handler=self.dbh)

        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        endpoint_type = kwargs["endpoint_type"]

        if (not endpoint_type or endpoint_type not in self.endpoint_types) and command != "add":
            info("Choose an endpoint type to attack, or all to attack any supported endpoint")
            endpoint_type = self.choose(self.endpoint_types + ["all"])

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
        if not d_dao.exists(main_domain):
            fatal(
                f"{main_domain} not found in the DB. you should run "
                f"`{highlight(f'python vortex -w {self.dbh.workspace} subdomain -D {main_domain} -c [enum|brute]')}`"
            )

        m_domain_obj = d_dao.find_by_name(main_domain)

        # Get all registered subdomains
        subdomains = d_dao.find_by_name_like(target)
        # Get all registered endpoints
        if is_subdomain(target) and validate_target_port(target):
            endpoints = [e_dao.find_by_name(target)]
        elif target == "*":
            # Get all registered endpoints
            endpoints = e_dao.list_all()
        else:
            endpoints = e_dao.find_by_name_like(target)

        if len(subdomains) == 0 or len(endpoints) == 0:
            fatal(
                f"{target} not found in the DB. Please run the following commands first:"
                f"- 1. Add subdomain: `{highlight(f'python vortex -w {self.dbh.workspace} subdomain -c add {target}')}`"
                f"- 2. Portscan:      `{highlight(f'python vortex -w {self.dbh.workspace} portscan -c single {target}')}`"
            )

        # Get all registered users
        users = u_dao.list_all()

        if command == "attack":
            for endpoint in endpoints:
                if endpoint_type and EndpointType.get_name(endpoint.endpoint_type) != endpoint_type:
                    continue

                subdomain = extract_domain(endpoint.target)
                subdomain_obj = d_dao.find_by_name(subdomain)

                additional_info = create_additional_info(
                    domain=m_domain_obj,
                    subdomain=subdomain_obj,
                    endpoint=endpoint
                )

                vpn_name = EndpointType.get_name(endpoint.endpoint_type)
                enumerator = OfficeEnumeratorFactory.from_name(vpn_name, endpoint.target)
                if not enumerator:
                    continue
                enumerator.setup(**additional_info)
                info(f"Running {enumerator.__class__.__name__} against {endpoint.target}")
                enumerator.parallel_login(users=users, passwords=passwords, use_leaks=use_leaks)
                for login in enumerator.found:
                    s_dao.save_new(login["username"], login["password"], endpoint.target)

        elif command == "add":

            if target is None:
                info("Please enter a target domain")
                target = self.wait_for_input()

            domain_obj = d_dao.find_by_name(target)
            if not domain_obj:
                domain_obj = Domain(did=0, name=target, email_format=None)

            for vt in EndpointType.value_list():
                vpn_name = EndpointType.get_name(vt)
                enumerator = OfficeEnumeratorFactory.from_name(vpn_name, target, group="dummy")
                if not enumerator:
                    continue
                enumerator.setup(**domain_obj.additional_info_json)
                if enumerator.validate():
                    success(f"{target} is a valid {vpn_name.upper()} target!")
                    endpoint_type = vt
                    in_db = False
                    for e in endpoints:
                        if f"{e.target}:{e.endpoint_type}" == f"{target}:{endpoint_type}":
                            in_db = True
                    if not in_db:
                        endpoint = Endpoint(target=target, endpoint_type=endpoint_type, eid=0)
                        e_dao.save(endpoint)
                else:
                    error(f"{target} does not seem a valid {vpn_name.upper()} target")
