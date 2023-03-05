from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.unified_user_data import UnifiedUserData
from lib.CrossLinked.crosslinked import crosslinked_run
from lib.theHarvester.theHarvester import theHarvester
from utils.utils import get_project_root, info


class Theharvester(Searcher):
    def __init__(self):
        super().__init__()
        self.domain = None
        self.proxy = None

    def setup(self, **kwargs):
        self.domain = kwargs.get("domain")
        self.proxy = kwargs.get("proxy", None)

    def search(self):
        if isinstance(self.domain, str):
            self.domain = [self.domain]
        if isinstance(self.domain, list):
            for domain in self.domain:
                try:
                    self.__search(domain)
                except Exception as e:
                    continue

    def __search(self, domain):
        args = {
            'active': True,
            'data_source': 'google',
            'domain': domain,
            'search_max': 100,
            'save_emails': False,
            'delay': 15.0,
            'url_timeout': 60,
            'num_threads': self.threads,
            'proxy': self.proxy
        }
        info("Starting passive/active search on Google")
        th = theHarvester(**args)
        users = th.go()
        for u in users:
            name = u.split("@")[0]
            name = name.replace(".", " ").replace("_", " ")
            self.uu_data.append(
                UnifiedUserData(
                    name=name,
                    email=u
                )
            )
