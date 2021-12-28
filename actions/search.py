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


class Search(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = ["linkedin", "pwndb", "google", "crosslinked"]

    def execute(self, **kwargs):
        self.dbh.connect()
        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        domain = kwargs["domain"]
        location = kwargs["location"]
        company = kwargs["company"]
        config = kwargs["config"]

        if domain is None:
            error("Domain field is required")
            info("Please enter a target domain")
            domain = self.wait_for_input()

        if command in ["linkedin", "crosslinked"] and company is None:
            error("Company name field is required")
            info("Please specify the company to search on LinkedIn")
            company = self.wait_for_input()

        dao = UserDao(handler=self.dbh)

        if command == "linkedin":
            # For LinkedIn, we need a masher
            masher = NameMasher()
            mail_format = self.dbh.get_email_format()
            if not mail_format:
                masher.select_format()
                self.dbh.set_email_format(masher.fmt)
            else:
                masher.fmt = mail_format

            info("Starting search on LinkedIn")
            try:
                from scripts.blues import LinkedIn
            except ModuleNotFoundError:
                error("Sorry, the LinkedIn module has been removed")
                exit(1)
            users = LinkedIn.execute_routine(company, location=location, config=config, reset=False)
            progress(f"Found {len(users)} LinkedIn accounts!", indent=2)
            info(f"Updating DB ...")
            for u in users.employee_list:
                if u.name.lower() == "linkedin member":
                    continue
                username = masher.mash(u.name.split(" ")[0], u.name.split(" ")[-1])
                email = f"{username}@{domain}"
                user = User(uid=0, name=u.name, username=username, email=email, role=u.role)
                dao.save(user)

        elif command == "crosslinked":
            # For CrossLinked, we need a masher
            masher = NameMasher()
            mail_format = self.dbh.get_email_format()
            if not mail_format:
                masher.select_format()
                self.dbh.set_email_format(masher.fmt)
            else:
                masher.fmt = mail_format

            kwargs = {
                'debug': int(self.config.get("CROSSLINKED", "debug") == 1),
                'timeout': float(self.config.get("CROSSLINKED", "timeout")),
                'jitter': float(self.config.get("CROSSLINKED", "jitter") == 1),
                'verbose': int(self.config.get("CROSSLINKED", "safe") == 1),
                'company_name': company,
                'header': [],
                'engine': ['google', 'bing'],
                'safe': int(self.config.get("CROSSLINKED", "safe") == 1),
                'nformat': '{f}{last}',
                'outfile': get_project_root().joinpath("data", "temp", self.config.get("CROSSLINKED", "outfile")),
                'proxy': []
            }

            info("Starting search on Google and Bing with CrossLinked")
            users = crosslinked_run(**kwargs)

            progress(f"Found {len(users)} LinkedIn accounts!", indent=2)
            info(f"Updating DB ...")
            for u in users:
                username = masher.mash(u["first"], u["last"])
                email = f"{username}@{domain}"

                user = User(
                    uid=0,
                    name=f'{u["first"].capitalize()} {u["last"].capitalize()}',
                    username=username,
                    email=email,
                    role=u["title"]
                )
                dao.save(user)

        elif command == "pwndb":
            info("Starting search on PwnDB")
            users = PwnDB(domain=domain).fetch()
            progress(f"Found {len(users)} leaked accounts!", indent=2)
            info(f"Updating DB ...")
            for u, leaks in users.items():
                if not u or u.strip() == "":
                    continue
                user = User(uid=0, name=None, username=u, email=f"{u}@{domain}", role=None)
                user.leaks = [Leak(leak_id=0, password=leak, uid=0) for leak in leaks]
                dao.save(user)
        elif command == "google":
            args = {
                'active': True,
                'data_source': 'google',
                'domain': domain,
                'search_max': 100,
                'save_emails': False,
                'delay': 15.0,
                'url_timeout': 60,
                'num_threads': 8
            }
            info("Starting passive/active search on Google")
            th = theHarvester(**args)
            mails = th.go()
            progress(f"Found {len(mails)} mail accounts!", indent=2)
            info(f"Updating DB ...")
            for m in mails:
                if not m or m.strip() == "":
                    continue
                u = m.split("@")[0]
                user = User(uid=0, name=None, username=u, email=m, role=None)
                dao.save(user)
        success(f"Done!")

