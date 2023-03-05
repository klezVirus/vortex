from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.unified_user_data import UnifiedUserData
from lib.CrossLinked.crosslinked import crosslinked_run
from utils.utils import get_project_root


class Crosslinked(Searcher):
    def __init__(self):
        super().__init__()
        self.company = None
        self.email_format = None
        self.masher = None

    def setup(self, **kwargs):
        self.company = kwargs.get("company")
        self.email_format = kwargs.get("email_format")
        self.masher = kwargs.get("masher")

    def search(self):
        kwargs = {
            'debug': int(self.config.get("CROSSLINKED", "debug") == 1),
            'timeout': float(self.config.get("CROSSLINKED", "timeout")),
            'jitter': float(self.config.get("CROSSLINKED", "jitter") == 1),
            'verbose': int(self.config.get("CROSSLINKED", "verbose") == 1),
            'company_name': self.company,
            'header': [],
            'engine': ['google', 'bing'],
            'safe': int(self.config.get("CROSSLINKED", "safe") == 1),
            'nformat':
                self.email_format.
                replace("{0:.1}", "{f}").
                replace("{1:.1}", "{l}").
                replace("{0}", "{first}").
                replace("{1}", "{last}"),
            'masher': self.masher,
            'outfile': get_project_root().joinpath("data", "temp", self.config.get("CROSSLINKED", "outfile")),
            'proxy': [] if not self.session.proxies else [self.session.proxies.get("http")]
        }
        users = crosslinked_run(**kwargs)
        for u in users:
            self.uu_data.append(
                UnifiedUserData(
                    name=f'{u["full"]}',
                    role=u["title"]
                )
            )
