from actions.action import Action
from db.dao.user import UserDao
from db.handler import DBHandler
from db.models.leak import Leak
from db.models.user import User
from lib.CrossLinked.crosslinked import crosslinked_run
from lib.theHarvester.theHarvester import theHarvester
from scripts.pwndb import PwnDB
from utils.namemash import NameMasher
from utils.utils import progress, info, success, error, get_project_root


class Api(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.commands = ["snusbase", "dehashed"]

    def execute(self, **kwargs):
        self.dbh.connect()
        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        dao = UserDao(handler=self.dbh)
        emails = [u.email for u in dao.list_all() if u.email]

        if command == "snusbase":
            info("Starting search on Snusbase")
            try:
                from scripts.snusbase import Snusbase
            except ModuleNotFoundError:
                error("Sorry, the LinkedIn module has been removed")
                exit(1)
            users = Snusbase.execute_routine(emails)
            progress(f"Found {len(users)} Leaked accounts!", indent=2)
            info(f"Updating DB ...")
            error("Not implemented yet")
            exit(1)

        if command == "dehashed":
            domains = kwargs.get("domain")
            if domains is None:
                error("Domain field is required")
                info("Please enter a target domain")
                domains = self.wait_for_input()

                # Listify the domain
            if domains.find(",") > -1:
                domains = domains.split(",")
            else:
                domains = [domains]

            info("Starting search on DeHashed")
            try:
                from scripts.dehashed import Dehashed
            except ModuleNotFoundError:
                error("Sorry, the DeHashed module has been removed")
                exit(1)
            Dehashed.execute_routine(domains, self.workspace)

        success(f"Done!")

