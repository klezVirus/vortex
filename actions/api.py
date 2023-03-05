from actions.action import Action
from utils.utils import progress, info, success, error, listify


class Api(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        for s in self.searchers():
            self.commands[s] = ["domain"]

    def execute(self, **kwargs):
        self.dbh.connect()
        command = kwargs["command"]
        domains = kwargs.get("domain")
        emails = self.dbms.get_users_mails(dfilter=domains)

        users = []
        if command == "snusbase":
            info("Starting search on Snusbase")
            try:
                from enumerators.api.snusbase import Snusbase
            except ModuleNotFoundError:
                error("Sorry, the Snusbase module has been removed")
                exit(1)
            users = Snusbase.execute_routine(emails)

        elif command == "dehashed":
            domains = listify(domains)
            info("Starting search on DeHashed")
            try:
                from enumerators.api.dehashed import Dehashed
            except ModuleNotFoundError:
                error("Sorry, the DeHashed module has been removed")
                exit(1)
            users = Dehashed.execute_routine(domains, self.workspace)

        elif command == "hunterio":
            info("Starting search on DeHashed")
            try:
                from enumerators.api.hunter import HunterIO
            except ModuleNotFoundError:
                error("Sorry, the HunterIO module has been removed")
                exit(1)
            users = HunterIO.execute_routine(domains, self.workspace)
        elif command == "intelx":
            info("Starting search on DeHashed")
            try:
                from enumerators.api.intelx import IntelX
            except ModuleNotFoundError:
                error("Sorry, the IntelX module has been removed")
                exit(1)
            users = IntelX.execute_routine(domains, self.workspace)

        progress(f"Found {len(users)} Leaked accounts!")
        self.dbms.save_users_from_uudata(users, domains)
        success(f"Done!")

