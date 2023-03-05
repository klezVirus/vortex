"""
COMING SOON
"""
from enumerators.interfaces.api import Api
from enumerators.interfaces.searcher import Searcher


class HunterIO(Searcher, Api):
    def __init__(self):
        super().__init__()
        self.API_ROOT = "https://api.hunter.io/v2/"
        self.base_params = {'api_key': self.api_keys[0]}
        self.domain = None
        self.account_info = None
        self.limit = 10

    def setup(self, **kwargs):
        self.domain = kwargs.get("domain")
        starting_api = self.api_keys[0]

        self.get_account_information()
        if self.api_available_credits == 0:
            print(f"API key {self.api_keys[0]} - 0 API credits left")
            self.rotate_key()
        while self.api_available_credits == 0 and self.api_keys[0] != starting_api:
            self.get_account_information()

        if self.api_available_credits == 0:
            self.get_account_information()
        if self.api_available_credits == 0:
            print("No IntelX API credits available")
        api_credits = str(self.api_available_credits) + "/" + str(self.api_total_credits)
        print(f"Using API key {self.api_keys[0]} - IntelX API credits: {api_credits}")

    def get_total_credits(self):
        pass

    def get_available_credits(self):
        pass

    def __extract_data(self, res):
        try:
            print(res.text)
            data = res.json()['data']
        except KeyError:
            return None
        return data

    def get_account_information(self):
        res = self.session.get(self.API_ROOT + "account", params=self.base_params)
        data = self.__extract_data(res)
        self.account_info = data
        if data.get("plan_level", 0) != 0:
            self.limit = 100
        self.api_total_credits = data.get("requests", {}).get("searches", {}).get("available")
        self.api_available_credits = self.api_total_credits - data.get("requests", {}).get("searches", {}).get("used")

    def rotate_key(self):
        api_key = self.api_keys.pop(0)
        self.api_keys.append(api_key)
        self.base_params = {'api_key': self.api_keys[0]}

    def search(self) -> tuple:
        params = self.base_params
        params['domain'] = self.domain
        params['limit'] = self.limit
        params['offset'] = 0
        params['type'] = "personal"

        res = self.session.get(self.API_ROOT + 'domain-search', params=params)
        data = self.__extract_data(res)
        if data is None:
            return None, None
        email_objects = data.get('emails', [])
        from utils.mashers.namemash import NameMasher
        masher = NameMasher()
        masher.fmt = data.get("pattern", "{first}.{last}")
        for eo in email_objects:
            try:
                first_name = eo.get("first_name")
                last_name = eo.get("last_name")

                self.add_user_info(
                    name=f"{first_name} {last_name}",
                    email=eo.get("value"),
                    role=eo.get("position"),
                )
            except Exception as e:
                continue
        return self.uu_data, self.results

    @staticmethod
    def execute_routine(domains: list, workspace: str):
        collector = HunterIO()
        collector.setup(domain=domains[0])
        collector.search()
        return collector.uu_data

