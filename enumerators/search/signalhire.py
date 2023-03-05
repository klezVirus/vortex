import re

from enumerators.interfaces.searcher import Searcher
from enumerators.search.structures.unified_user_data import UnifiedUserData
from utils.utils import get_project_root, info, std_soup, warning, error


class Signalhire(Searcher):
    def __init__(self):
        super().__init__()
        self.company = None
        self.current_page = 1
        self.page_limit = 5
        self.__base_url = "https://signalhire.com"
        self.base_url = self.__base_url
        self.use_aws = False

    @property
    def url(self):
        return self.base_url + "/companies/{}/employees?page={}"

    def setup(self, **kwargs):
        self.company = kwargs.get("company")
        self.current_page = kwargs.get("page", 1)
        if kwargs.get("aws"):
            self.use_aws = True
            self.setup_awsm(self.base_url, api_count=1)

    def search(self):
        if self.aws_manager:
            self.base_url = self.aws_manager.list_urls(self.__base_url)[0]
        info("Starting active search on SignalHire")
        while self.current_page <= self.current_page + self.page_limit:
            try:
                url = self.url.format(self.company.lower().replace(" ", "-"), self.current_page)
                if self.current_page % 5 == 1:  # We start from page 1, we refresh the IP every 5 pages
                    print(url)
                    self.on_fire()
                print(self.session.proxies)
                response = self.session.get(url)
                if response.status_code != 200:
                    error("Failed to get response from SignalHire")
                    break
                soup = std_soup(response)

                if self.current_page == 1:
                    number_p = soup.find("p", {"class": "b-cp-info__descr"})
                    if number_p is not None:
                        number_of_employees = re.search(r"\d+", number_p.get_text())
                        if number_of_employees is not None:
                            number_of_employees = int(number_of_employees.group(0))
                            info(f"Found {number_of_employees} employees on SignalHire")
                            self.page_limit = number_of_employees // 56 if self.use_aws else 5 * (len(self.oxy_manager.proxies) + 1)

                ttable = []
                tables = soup.find_all("table", {"class": "table table-bordered"})
                if len(tables) == 0:
                    return
                for table in tables:
                    records = table.find_all("tr")
                    if len(records) == 0:
                        continue
                    for record in records:
                        try:
                            ttable.append([x.get_text().strip() for x in record.find_all("td") if x is not None])
                        except:
                            continue

                for u in ttable:
                    self.uu_data.append(
                        UnifiedUserData(
                            name=u[0],
                            role=u[1],
                            location=u[2],
                            email=u[3]
                        )
                    )
            except Exception as e:
                warning(f"Exception: {e}")