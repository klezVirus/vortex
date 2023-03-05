from actions.action import Action
from db.dao.domain import DomainDao
from db.dao.leak import LeakDao
from db.dao.user import UserDao
from db.models.leak import Leak
from db.models.user import User
from enumerators.factories import SearcherFactory
from utils.mashers.namemash import NameMasher
from utils.utils import progress, info, success, error, get_project_root, listify


class Search(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        for s in self.searchers():
            self.commands[s] = ["domain", "company", "email_format"]
        self.no_child_process = True

    def execute(self, **kwargs):
        self.dbh.connect()
        # change all kwargs[..] with kwargs.get(..)
        command = kwargs.get("command")
        domains = kwargs.get("domain")
        location = kwargs.get("location")
        title = kwargs.get("title")
        company = kwargs.get("company")
        current_company = kwargs.get("current_company")
        config = kwargs.get("config")
        otp = kwargs.get("otp")
        email_format = kwargs.get("email_format")
        _filter = kwargs.get("filter")
        aws = kwargs.get("aws")

        # Listify the domain
        domains = listify(domains)

        masher = NameMasher()
        masher.fmt = email_format

        # Unified Argument List for Searchers
        kwargs = {
            "company": company,  # Company Name
            "email_format": email_format,  # Email Format
            "masher": masher,  # Name Masher
            "domain": domains,
            "location": location,
            "current_company": current_company,
            "title": title,
            "filter": _filter,
            "otp": otp,
            "autosave": True,
            "reset": False,
            "aws": aws
        }

        searcher = SearcherFactory.from_name(command)
        if searcher is None:
            error("Error setting up the searcher")
            return
        searcher.setup(**kwargs)

        searcher.safe_search()

        user_counter = 0
        leak_counter = 0
        for uu in searcher.uu_data:
            try:
                uu.normalize(masher, domains[0])  # Normalize the data
                uid = self.dbms.save_user_from_uudata(uu)  # Save the user
                user_counter += 1
                if any([x not in [None, ""] for x in [uu.password, uu.phash, uu.phone, uu.address]]):
                    self.dbms.save_leak_from_uudata(uu, uid)
                    leak_counter += 1
            except Exception as e:
                error(f"Exception: {e}")
        success(f"{user_counter} users and {leak_counter} leaks inserted in the DB")
        success(f"Done!")

