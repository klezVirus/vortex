import queue
from concurrent.futures.thread import ThreadPoolExecutor

import dns

from actions.action import Action
from db.dao.domain import DomainDao
from db.dao.endpoint import EndpointDao
from db.models.domain import Domain
from lib.Amass import Amass
from lib.Sublist3r.sublist3r import main
from recon.discover import DomainDiscovery
from utils.namemash import NameMasher
from utils.utils import *


class Subdomain(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = ["enum", "brute", "add"]
        ttl = time_label()
        self.__temp_domains = str(get_project_root().joinpath("data", "temp", f"subdomains-{workspace}-{ttl}.csv"))
        self.__temp_origins = str(get_project_root().joinpath("data", "temp", f"origins-{workspace}-{ttl}.csv"))
        self.__objects = queue.Queue()

    def add_to_objects(self, value):
        self.lock.acquire()
        self.__queue.put(value, block=True, timeout=1)
        self.lock.release()

    def save(self, what, where, headers: list = None):
        with open(where, "w") as out:
            if headers and len(headers) > 0:
                out.write(",".join(headers))
            if isinstance(what, str):
                out.write(what)
            elif isinstance(what, list):
                for line in what:
                    out.write(line + "\n")

    def execute(self, **kwargs):
        self.dbh.connect()
        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        domain = kwargs["domain"]
        __resolve = kwargs["resolve"]
        if domain is None:
            error("Domain field is required")
            info("Please provide a target domain")
            domain = self.wait_for_input()

        e_dao = EndpointDao(handler=self.dbh)
        d_dao = DomainDao(handler=self.dbh)

        domain_obj = d_dao.find_by_name(domain)
        if not domain_obj:
            info("First time analysing this domain. What e-mail format should be used?")
            masher = NameMasher()
            masher.select_format()
            domain_obj = Domain(did=0, name=domain, email_format=masher.fmt)

            info("Starting general DNS enumeration and MS recon")
            discover = DomainDiscovery(domain)
            additional_info = {
                "DNS": {
                    "MX": discover.get_mx_records(),
                    "TXT": discover.get_txt_records()
                },
                "Microsoft": {
                    "UserRealm": discover.get_userrealm(),
                    "OpenID": discover.get_openid_configuration(),
                    "MS-Domains": discover.get_msol_domains(),
                    "MS-Tenants": discover.get_onedrive_tenant_names(),
                    "Skype": None
                }
            }
            domain_obj.additional_info_json = additional_info
            d_dao.save(domain_obj)

        db_endpoints = [e.target for e in e_dao.list_all()]

        brute = False
        skip = False
        start = time.time()
        if command == "enum":
            info("Starting subdomain passive enumeration")
        elif command == "brute":
            info("Starting subdomain bruteforce... can require some time")
            brute = True
        elif command == "add":
            if not is_subdomain(domain):
                fatal(f"{domain} is not a subdomain, execute a subdomain enumeration instead")
            info(f"Adding {domain}...")
            skip = True
        else:
            error("Unknown command")
            exit(1)

        if not skip:
            info("Would you like to use Sublist3r or Amass?")
            subdomains = []
            if choose(["Amass", "Sublist3r"]) == "Sublist3r":
                subdomains = main(
                    domain=domain,
                    threads=30,
                    enable_bruteforce=brute,
                    verbose=False,
                    engines=None,
                    silent=True,
                    savefile=None,
                    ports=None
                )
            else:
                amass = Amass(domain=domain)
                amass.passive = not brute
                amass.enumerate()
                subdomains = amass.extract_domain_list()
        else:
            subdomains = [domain]
        progress(f"Found {len(subdomains)} subdomains", indent=2)

        if __resolve:
            info(f"Trying to resolve subdomains with default resolver")
            __subdomains = {}
            for s in subdomains:
                __subdomains[s] = {"DNS": {"A": None, "AAAA": None}}
            with ThreadPoolExecutor(max_workers=20) as executor:
                for result in executor.map(Subdomain.resolve, __subdomains.keys()):
                    if any([result[1], result[2]]):
                        __subdomains[result[0]]["DNS"] = {
                            "A": result[1],
                            "AAAA": result[2]
                        }
                    else:
                        error(f"{result[0]} doesn't exist")
                        subdomains.remove(result[0])
        progress(f"Resolved {len(subdomains)} subdomains", indent=2)
        info(f"Updating DB...")
        for sub in subdomains:
            sd = Domain(did=0, name=sub, email_format=domain_obj.email_format, additional_info=__subdomains[sub])
            if d_dao.exists(sd):
                error(f"{sub} already in the DB. Skipping", indent=2)
            else:
                d_dao.save(sd)
        debug(f"Elapsed time: {time.time() - start}", indent=2)
        success("Done")

    @staticmethod
    def resolve(domain):
        debug(f"Resolving {domain}")
        d = DomainDiscovery(domain)
        return domain, d.get_a_records(), d.get_aaaa_records()
