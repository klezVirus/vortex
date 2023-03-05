"""
COMING SOON
"""
import json
import time

from enumerators.interfaces.api import Api
from enumerators.interfaces.searcher import Searcher
from utils.utils import fatal, info


class IntelX(Searcher, Api):
    def __init__(self):
        super().__init__()
        if len(self.api_keys) == 0:
            self.api_keys = ["01a61412-7629-4288-b18a-b287266f2798", "ac572eea-3902-4e9a-972d-f5996d76174c"]
            self.API_ROOT = "https://public.intelx.io"
        else:
            self.API_ROOT = "https://2.intelx.io"

        self.session.headers.update({'x-key': self.api_keys[0]})
        self.domain = None

    def setup(self, **kwargs):
        self.domain = kwargs.get("domain")
        starting_api = self.api_keys[0]

        self.api_total_credits = self.get_total_credits()
        self.api_available_credits = self.get_available_credits()
        if self.api_available_credits == 0:
            print(f"API key {self.api_keys[0]} - 0 API credits left")
            self.rotate_key()
        while self.api_available_credits == 0 and self.api_keys[0] != starting_api:
            self.api_total_credits = self.get_total_credits()
            self.api_available_credits = self.get_available_credits()

        if self.api_available_credits == 0:
            self.switch_to_public_api()
            self.api_total_credits = self.get_total_credits()
            self.api_available_credits = self.get_available_credits()
        if self.api_available_credits == 0:
            print("No IntelX API credits available")
        api_credits = str(self.api_available_credits) + "/" + str(self.api_total_credits)
        print(f"Using API key {self.api_keys[0]} - IntelX API credits: {api_credits}")

    def get_total_credits(self):
        return self.GET_CAPABILITIES()["paths"]["/phonebook/search"]["CreditMax"]

    def get_available_credits(self):
        return self.GET_CAPABILITIES()["paths"]["/phonebook/search"]["Credit"]

    def search(self) -> tuple:
        blocks = self.phonebooksearch(
            self.domain,
            maxresults=100000,
            buckets=[],
            timeout=5,
            datefrom="",
            dateto="",
            sort=4,
            media=0,
            terminate=[],
            target=2
        )
        for block in blocks:
            for result in block.get('selectors', []):
                if result.get('selectortype', 0) == 1:
                    email = result.get('selectorvalue', "")
                    user = email.split("@")[0]
                    self.add_user_info(email=email, username=user)
        return self.uu_data, self.results

    @staticmethod
    def execute_routine(domains: list, workspace: str):
        ix = IntelX()
        ix.setup(domain=domains[0])
        ix.search()
        return ix.uu_data

    def rotate_key(self):
        api_key = self.api_keys.pop(0)
        self.api_keys.append(api_key)
        self.session.headers.update({'x-key': self.api_keys[0]})

    def switch_to_public_api(self):
        self.API_ROOT = "https://public.intelx.io"
        self.api_keys = ["01a61412-7629-4288-b18a-b287266f2798", "ac572eea-3902-4e9a-972d-f5996d76174c"]
        self.session.headers.update({'x-key': self.api_keys[0]})

    @staticmethod
    def get_error(code):
        """
        Get error string by respective HTTP response code.
        """
        if code == 200:
            return "200 | Success"
        if code == 204:
            return "204 | No Content"
        if code == 400:
            return "400 | Bad Request"
        if code == 401:
            return "401 | Unauthorized"
        if code == 402:
            return "402 | Payment required."
        if code == 404:
            return "404 | Not Found"

    @staticmethod
    def cleanup_treeview(treeview):
        """
        Cleans up treeview output from the API.
        """
        lines = []
        for line in treeview.split("\r\n"):
            if '<a href' not in line:
                lines.append(line)
        return lines

    def GET_CAPABILITIES(self):
        """
        Return a JSON object with the current user's API capabilities
        """
        r = self.session.get(f"{self.API_ROOT}/authenticate/info")
        return r.json()

    def FILE_PREVIEW(self, ctype, mediatype, format, sid, bucket='', e=0, lines=8):
        """
        Show a preview of a file's contents based on its storageid (sid).
        """
        current_key = self.api_keys[0]
        r = self.session.get(
            f"{self.API_ROOT}/file/preview?c={ctype}&m={mediatype}&f={format}&sid={sid}&b={bucket}&e={e}&l={lines}&k={current_key}")
        return r.text

    def FILE_VIEW(self, ctype, mediatype, sid, bucket='', escape=0):
        """
        Show a file's contents based on its storageid (sid), convert to text where necessary.
        """
        current_key = self.api_keys[0]
        if mediatype == 23 or mediatype == 9:  # HTML
            file_format = 7
        elif mediatype == 15:  # PDF
            file_format = 6
        elif mediatype == 16:  # Word
            file_format = 8
        elif mediatype == 18:  # PowerPoint
            file_format = 10
        elif mediatype == 25:  # Ebook
            file_format = 11
        elif mediatype == 17:  # Excel
            file_format = 9
        elif ctype == 1:       # Text
            file_format = 0
        else:
            file_format = 1
        r = self.session.get(
            f"{self.API_ROOT}/file/view?f={file_format}&storageid={sid}&bucket={bucket}&escape={escape}&k={current_key}"
        )
        return r.text

    def FILE_READ(self, id, type=0, bucket="", filename=""):
        """
        Read a file's raw contents. Use this for direct data download.
        """
        r = self.session.get(f"{self.API_ROOT}/file/read?type={type}&systemid={id}&bucket={bucket}", stream=True)
        with open(f"{filename}", "wb") as f:
            f.write(r.content)
            f.close()
        return True

    def FILE_TREE_VIEW(self, sid):
        """
        Show a treeview of an item that has multiple files/folders
        """
        current_key = self.api_keys[0]
        try:
            r = self.session.get(f"{self.API_ROOT}/file/view?f=12&storageid={sid}&k={current_key}", timeout=5)
            if "Could not generate" in r.text:
                return False
            return r.text
        except:
            return False

    def INTEL_SEARCH(self, term, maxresults=100, buckets=None, timeout=5, datefrom="", dateto="", sort=4, media=0,
                     terminate=None):
        """
        Launch an Intelligence X Search
        """
        if not buckets:
            buckets = []
        if not terminate:
            terminate = []
        p = {
            "term": term,
            "buckets": buckets,
            "lookuplevel": 0,
            "maxresults": maxresults,
            "timeout": timeout,
            "datefrom": datefrom,
            "dateto": dateto,
            "sort": sort,
            "media": media,
            "terminate": terminate
        }
        r = self.session.post(self.API_ROOT + '/intelligent/search', json=p)
        if r.status_code == 200:
            return r.json()['id']
        else:
            return r.status_code

    def INTEL_SEARCH_RESULT(self, _id, limit):
        """
        Return results from an initialized search based on its ID
        """
        r = self.session.get(self.API_ROOT + f'/intelligent/search/result?id={_id}&limit={limit}')
        if r.status_code == 200:
            return r.json()
        else:
            return r.status_code

    def INTEL_TERMINATE_SEARCH(self, uuid):
        """
        Terminate a previously initialized search based on its UUID.
        """
        r = self.session.get(self.API_ROOT + f'/intelligent/search/terminate?id={uuid}')
        if r.status_code == 200:
            return True
        else:
            return r.status_code

    def PHONEBOOK_SEARCH(self, term, maxresults=100, buckets: list = None, timeout=5, datefrom="", dateto="", sort=4, media=0,
                         terminate: list = None, target=0):
        """
        Initialize a phonebook search and return the ID of the task/search for further processing
        """
        if not buckets:
            buckets = []
        if not terminate:
            terminate = []
        p = {
            "term": term,
            "buckets": buckets,
            "lookuplevel": 0,
            "maxresults": maxresults,
            "timeout": timeout,
            "datefrom": datefrom,
            "dateto": dateto,
            "sort": sort,
            "media": media,
            "terminate": terminate,
            "target": target
        }
        r = self.session.post(self.API_ROOT + '/phonebook/search', json=p)
        if r.status_code == 200:
            return r.json()['id']
        else:
            return r.status_code

    def PHONEBOOK_SEARCH_RESULT(self, id, limit=1000, offset=-1):
        """
        Fetch results from a phonebook search based on ID.
        """
        r = self.session.get(self.API_ROOT + f'/phonebook/search/result?id={id}&limit={limit}&offset={offset}')
        if r.status_code == 200:
            return r.json()
        else:
            return r.status_code

    def query_results(self, rid, limit):
        """
        Query the results from an intelligent search.
        Meant for usage within loops.
        """
        results = self.INTEL_SEARCH_RESULT(rid, limit)
        return results

    def query_pb_results(self, rid, limit):
        """
        Query the results fom a phonebook search.
        Meant for usage within loops.
        """
        results = self.PHONEBOOK_SEARCH_RESULT(rid, limit)
        return results

    def history(self, storage_id):
        """
        Fetch historical results for a domain.
        """
        current_key = self.api_keys[0]
        r = self.session.get(self.API_ROOT + f'/file/view?f=13&storageid={storage_id}&k={current_key}')
        if r.status_code == 200:
            return r.json()
        else:
            return r.status_code

    def __search(self, term, maxresults=100, buckets: list = None, timeout=5, datefrom="", dateto="", sort=4, media=0,
               terminate: list = None):
        """
        Conduct a simple search based on a search term.
        Other arguments have default values set, however they can be overridden to complete an advanced search.
        """
        if not buckets:
            buckets = []
        if not terminate:
            terminate = []
        results = []
        done = False
        search_id = self.INTEL_SEARCH(term, maxresults, buckets, timeout, datefrom, dateto, sort, media, terminate)
        if len(str(search_id)) <= 3:
            print(f"[!] intelx.INTEL_SEARCH() Received {self.get_error(search_id)}")
            return {'records': []}
        while not done:
            time.sleep(1)  # let's give the backend a chance to aggregate our data
            r = self.query_results(search_id, maxresults)
            for a in r['records']:
                results.append(a)
            maxresults -= len(r['records'])
            if r['status'] == 1 or r['status'] == 2 or maxresults <= 0:
                if maxresults <= 0:
                    self.INTEL_TERMINATE_SEARCH(search_id)
                done = True
        return {'records': results}

    def phonebooksearch(self, term, maxresults=1000, buckets: list = None, timeout=5, datefrom="", dateto="", sort=4,
                        media=0, terminate: list = None, target=0):
        """
        Conduct a phonebook search based on a search term.
        Other arguments have default values set, however they can be overridden to complete an advanced search.
        """
        if not buckets:
            buckets = []
        if not terminate:
            terminate = []
        results = []
        done = False
        search_id = self.PHONEBOOK_SEARCH(term, maxresults, buckets, timeout, datefrom, dateto, sort, media, terminate,
                                          target)
        if len(str(search_id)) <= 3:
            print(f"[!] intelx.PHONEBOOK_SEARCH() Received {self.get_error(search_id)}")
            return {'records': []}
        while not done:
            time.sleep(1)  # let's give the backend a chance to aggregate our data
            r = self.query_pb_results(search_id, maxresults)
            results.append(r)
            maxresults -= len(r['selectors'])
            if r['status'] == 1 or r['status'] == 2 or maxresults <= 0:
                if maxresults <= 0:
                    self.INTEL_TERMINATE_SEARCH(search_id)
                done = True
        return results

    def stats(self, search):
        stats = {}
        for record in search['records']:
            if record['bucket'] not in stats:
                stats[record['bucket']] = 1
            else:
                stats[record['bucket']] += 1
        return json.dumps(stats)

    def selectors(self, document):
        current_key = self.api_keys[0]
        r = self.session.get(self.API_ROOT + f'/item/selector/list/human?id={document}&k={current_key}')
        return r.json()['selectors']