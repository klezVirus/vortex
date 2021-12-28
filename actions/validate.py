import os.path

from colorama import Fore

from actions.action import Action
from db.dao.endpoint import EndpointDao
from db.dao.login import LoginDao
from db.dao.user import UserDao
from db.enums.types import EndpointType
from enumerators.factories import VpnEnumeratorFactory

from db.models.user import User
from utils.utils import success, error, info, progress
from validators.o365creeper import O365Creeper


class Validate(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = ["users", "endpoints"]

    def execute(self, **kwargs):
        self.dbh.connect()
        u_dao = UserDao(handler=self.dbh)
        e_dao = EndpointDao(handler=self.dbh)
        s_dao = LoginDao(handler=self.dbh)

        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        # Get all registered endpoints
        endpoints = e_dao.list_all()
        # Get all registered users
        users = u_dao.list_all()

        # Keep trace of invalid objects
        invalid = []

        if command == "users":
            validator = O365Creeper()
            for u in users:
                kwargs = {"email": u.email}
                if validator.execute(**kwargs):
                    success(f"{u.email} is a valid O365 account!")
                else:
                    error(f"{u.email} is not a valid O365 account.")
                    invalid.append(u)

        if command == "endpoints":

            for endpoint in endpoints:
                vpn_name = EndpointType.get_name(int(endpoint.endpoint_type))
                enumerator = VpnEnumeratorFactory.from_name(vpn_name, endpoint.target, group="dummy")
                if enumerator.validate():
                    success(f"{endpoint.target} is a {vpn_name} target!")
                else:
                    error(f"{endpoint.target} is not a {vpn_name} target!")
                    invalid.append(endpoint)

        if len(invalid) == 0:
            exit(1)
        else:
            info(f"Found {len(invalid)} invalid objects. Delete?")
            choice = self.wait_for_choice()
            if not choice:
                exit(1)
            dao = u_dao if isinstance(invalid[0], User) else e_dao
            for obj in invalid:
                progress(f"Deleting {obj.__class__.__name__}: {obj.to_string()}")
                dao.delete(obj)
