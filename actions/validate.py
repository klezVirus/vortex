import traceback

from actions.action import Action
from db.dao.endpoint import EndpointDao
from db.dao.etype import EtypeDao
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
        valid = []

        if command == "users":
            validator = O365Creeper()
            for u in users:
                kwargs = {"email": u.email}
                try:
                    if validator.execute(**kwargs):
                        success(f"{u.email} is a valid O365 account!")
                        valid.append(u)
                    else:
                        error(f"{u.email} is not a valid O365 account.")
                        invalid.append(u)
                except KeyboardInterrupt:
                    exit(1)
                except Exception as e:
                    traceback.print_exc()
                    error(f"Exception: {e}")
                    continue

        if command == "endpoints":
            et_dao = EtypeDao(self.dbh)
            for endpoint in endpoints:
                vpn_type = et_dao.find_by_id(endpoint.etype_ref)
                vpn_name = vpn_type.name
                enumerator = VpnEnumeratorFactory.from_name(vpn_name, endpoint.target, group="dummy")
                try:
                    result, res = enumerator.validate()
                    if result:
                        success(f"{endpoint.target} is a {vpn_name} target!")
                    else:
                        error(f"{endpoint.target} is not a {vpn_name} target!")
                        invalid.append(endpoint)
                except KeyboardInterrupt:
                    exit(1)
                except Exception as e:
                    error(f"Exception: {e}")
                    continue

        if len(invalid) == 0:
            exit(1)
        else:
            info(f"Found {len(invalid)} invalid objects. Delete?")
            choice = self.wait_for_choice()
            if not choice:
                exit(1)
            try:
                dao = u_dao if isinstance(invalid[0], User) else e_dao
                for obj in invalid:
                    progress(f"Deleting {obj.__class__.__name__}: {obj.to_string()}")
                    dao.delete(obj)
            except Exception as e:
                error(f"Exception: {e}")
            try:
                if isinstance(valid[0], User):
                    dao = u_dao

                    for obj in valid:
                        progress(f"Deleting {obj.__class__.__name__}: {obj.to_string()}")
                        dao.set_valid(obj)
            except Exception as e:
                error(f"Exception: {e}")
