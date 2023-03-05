import queue
from concurrent.futures.thread import ThreadPoolExecutor

from actions.action import Action
from db.dao.domain import DomainDao
from db.dao.endpoint import EndpointDao
from db.models.domain import Domain
from lib.Amass import Amass
from lib.Sublist3r.sublist3r import main
from recon.discover import DomainDiscovery
from utils.mashers.namemash import NameMasher
from utils.utils import *


class Subdomain(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = {
            "enum": ["domain", "tool", "email_format"],
            "brute": ["domain", "tool", "email_format"],
            "add": ["domain", "email_format"],
            "resolve": ["domain"],
            "takeover": ["domain"],
            "clean": []
        }
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
        domain = kwargs["domain"]
        email_format = kwargs.get("email_format")
        __resolve = kwargs.get("resolve")
        __takeover = kwargs.get("takeover")
        __tool = kwargs.get("tool")

        # If command is "Clean", delete all subdomains without DNS records and exit
        if command == "clean":
            info("Cleaning subdomains...")
            self.dbms.domain_dao.delete_if_no_dns()
            exit(1)

        domain_obj = self.dbms.get_domain(domain)
        if not domain_obj:
            info("First time analysing this domain. Running general checks.")
            masher = NameMasher()
            masher.fmt = email_format
            info(f"Using e-mail address format: `{email_format}`")
            domain_obj = Domain(did=0, name=domain, email_format=masher.fmt)

            info("Starting general DNS enumeration and MS recon")
            discover = DomainDiscovery(domain)
            dns = {
                "MX": discover.get_mx_records(),
                "NS": discover.get_ns_records(),
                "A": discover.get_a_records(),
                "CNAME": discover.get_cname_records(),
                "AAAA": discover.get_aaaa_records(),
                "TXT": discover.get_txt_records()
            }

            additional_info = {
                "Microsoft": {
                    "UserRealm": discover.get_userrealm(),
                    "OpenID": discover.get_openid_configuration(),
                    "MS-Domains": discover.get_msol_domains(),
                    "MS-Tenants": [
                        {
                            "name": tenant,
                            "confirmed": False,
                            "confirmed-via": ""
                        } for tenant in discover.tenant_names
                    ] + [
                        {
                            "name": tenant,
                            "confirmed": True,
                            "confirmed-via": "OneDrive"
                        } for tenant in discover.get_onedrive_tenant_names()
                    ],
                    "Autodiscover": discover.autodiscover(),
                    "OWA": discover.owa(),
                    "Skype": None
                }
            }
            domain_obj.additional_info_json = additional_info
            domain_obj.dns_json = dns
            self.dbms.save_domain(domain_obj)

        db_domains = self.dbms.get_subdomains(domain)

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
        elif command == "resolve":
            info(f"Resolving {domain} and its subdomains (if any)...")
            skip = True
            __resolve = True
        elif command == "takeover":
            info(f"Check for subdomain takeover on `{domain}` (if any)...")
            skip = True
            __takeover = True
        else:
            error("Unknown command")
            exit(1)

        if not skip:
            info(f"Starting subdomain enumeration with `{__tool}`")
            subdomains = []
            if __tool == "Sublist3r":
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
        elif command in ["resolve", "takeover"]:
            subdomains = self.dbms.get_subdomains(domain)
        else:
            subdomains = [domain]
        progress(f"Found {len(subdomains)} subdomains")

        __subdomains = {}
        for s in subdomains:
            if s not in db_domains:
                __subdomains[s] = {
                    "DNS": {"A": None, "AAAA": None, "CNAME": None, "MX": None, "NS": None, "TXT": None},
                    "Frontable": None,
                    "Takeover": None
                }
            else:
                db_obj = self.dbms.get_domain(s)
                __subdomains[s] = {
                    "DNS": db_obj.dns_json,
                    "Frontable": db_obj.frontable_json,
                    "Takeover": db_obj.takeover_json
                }

        if __resolve:
            info(f"Trying to resolve subdomains with default resolver")
            with ThreadPoolExecutor(max_workers=20) as executor:
                for result in executor.map(Subdomain.resolve, __subdomains.keys()):
                    if any([result[1], result[2]]):
                        __subdomains[result[0]]["DNS"] = result[1]
                        __subdomains[result[0]]["Frontable"] = result[2]
                    else:
                        error(f"{result[0]} doesn't exist")
                        subdomains.remove(result[0])
            progress(f"Resolved {len(subdomains)} subdomains")

        if __takeover:
            takover_args = [(s, __subdomains[s]["DNS"]) for s in __subdomains.keys()]
            info(f"Trying to check for subdomain takeover")
            vulnerable = 0
            with ThreadPoolExecutor(max_workers=20) as executor:
                for result in executor.map(Subdomain.takeover, takover_args):
                    __subdomains[result[0]]["Takeover"] = result[1]
                    if result[1]:
                        success(f"{result[0]} is vulnerable to takeover")
                        vulnerable += 1
                    else:
                        error(f"{result[0]} is not vulnerable to takeover")
            progress(f"Found {vulnerable} subdomains vulnerable to takeover")

        info(f"Updating DB...")
        for sub in subdomains:
            sd = Domain(
                did=0,
                name=sub,
                email_format=domain_obj.email_format,
                dns=__subdomains[sub]["DNS"],
                frontable=__subdomains[sub]["Frontable"],
                takeover=__subdomains[sub]["Takeover"]
            )
            if self.dbms.exists_domain(sd) and command != "resolve":
                error(f"{sub} already in the DB. Skipping")
            elif self.dbms.exists_domain(sd) and command == "resolve":
                self.dbms.update_domain(sd)
            else:
                self.dbms.save_domain(sd)

        debug(f"Elapsed time: {time.time() - start}")
        success("Done")

    @staticmethod
    def resolve(domain):
        debug(f"Resolving {domain}")
        d = DomainDiscovery(domain)
        return domain, {
            "A": d.get_a_records(),
            "AAAA": d.get_aaaa_records(),
            "CNAME": d.get_cname_records(),
            "MX": d.get_mx_records(),
            "NS": d.get_ns_records(),
            "TXT": d.get_txt_records()
        }, d.is_frontable()

    @staticmethod
    def takeover(keys: tuple):
        domain = keys[0]
        dns = keys[1]
        from utils.misc.takeover import can_be_taken_over
        return domain, can_be_taken_over(domain, dns)
