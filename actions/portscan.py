import queue
import re
import threading
import timeit
from _queue import Empty

from db.dao.domain import DomainDao
from db.dao.endpoint import EndpointDao
from db.dao.etype import EtypeDao
from db.enums.types import EndpointType
from db.models.endpoint import Endpoint
from enumerators.factories import VpnEnumeratorFactory, OfficeEnumeratorFactory
from enumerators.parallel import DetectWorker
from lib.Amass import Amass
from lib.Sublist3r.sublist3r import main, PortScanner

from actions.action import Action
from utils.utils import *


class Portscan(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = ["vpn", "office"]
        ttl = time_label()
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
        command = kwargs.get("command")
        if not command or command not in self.commands:
            command = self.choose_command()

        _filter = kwargs.get("filter")
        _no_validate = kwargs.get("no_validate")
        ports = kwargs.get("ports")
        domain = kwargs.get("domain")
        if domain is None:
            error("Domain field is required")
            info("Please provide a target domain")
            domain = self.wait_for_input()

        e_dao = EndpointDao(handler=self.dbh)
        etype_dao = EtypeDao(handler=self.dbh)
        d_dao = DomainDao(handler=self.dbh)

        db_endpoints = [e.target for e in e_dao.list_all()]

        start = time.time()
        m_domain_obj = d_dao.find_by_name(extract_domain(domain))

        oracle = {
            "domain": m_domain_obj,
            "subdomains": {},
            "endpoints": {}
        }

        info(f"Starting portscan against {highlight(domain)}")

        if is_subdomain(domain):
            db_domains = [d_dao.find_by_name(domain)]
        elif domain == "*":
            # Get all registered endpoints
            db_domains = d_dao.list_all()
        else:
            db_domains = d_dao.find_by_name_like(domain)

        if _filter:
            _fr = re.compile(_filter, re.IGNORECASE)
            db_domains = [d for d in db_domains if _fr.search(d.name)]

        for d in db_domains:
            oracle["subdomains"] = {d.name: d.additional_info_json}

        subdomains = [x.name for x in db_domains]
        progress(f"Found {len(subdomains)} subdomains in the database", indent=2)
        if not ports:
            ports = self.config.get("SCANNER", "ports")

        if not ports:
            ports = [443, 1443, 8443, 10443]
        else:
            ports = [int(p.strip()) for p in ports.split(",") if validate_port(p.strip())]

        origins = [f"{d}:{p}" for d in subdomains for p in ports]
        origins = [o for o in origins if not e_dao.exists_categorised(o)]

        origins_to_scan = [o for o in origins if not e_dao.exists(o)]

        if len(origins_to_scan) > 0:
            info(f"Enumerating potential VPN/MS endpoints (HTTP[S] on {', '.join([str(x) for x in ports])})")
            scanner = PortScanner(origins=origins_to_scan)
            scanner.run()
            origins = scanner.origins
            progress(f"Found {len(origins)} origins hosting a running service", indent=2)
            self.save(origins, self.__temp_origins)
            debug(f"Elapsed time: {time.time() - start}", indent=2)
        else:
            info(f"All origins were already found in the DB. Skipping port scan.")
            progress(f"Validating {len(origins)} in the DB", indent=2)

        if not _no_validate:
            if command == "vpn":
                info(f"Trying to detect hosts with VPN web-login")
                self.parallel_validate(domains=origins, **oracle)
                progress(f"Found {len(self.endpoints)} hosts with a VPN web login", indent=2)

            elif command == "office":
                info(f"Trying to detect hosts with MS on premise web-login")
                self.parallel_validate_office(domains=origins, **oracle)
                progress(f"Found {len(self.endpoints)} hosts with a ME on-premise web login", indent=2)

            debug(f"Elapsed time: {time.time() - start}", indent=2)
        else:
            info(f"Validation skipped.")
        info(f"Updating DB...")
        for endpoint in self.endpoints:
            vpn_name = EndpointType.get_name(endpoint['endpoint_type'])
            if not vpn_name:
                vpn_etid = 1
            else:
                vpn_etid = etype_dao.find_by_name(vpn_name.upper()).etid

            origin = endpoint['endpoint']
            endpoint_info = None
            if endpoint.get("additional_info"):
                endpoint.get("additional_info", {}).get("Endpoint")

            ep = Endpoint(
                eid=0,
                target=origin,
                email_format=d_dao.get_email_format(extract_domain(origin)),
                etype_ref=EndpointType.UNKNOWN.value,
                additional_info=endpoint_info
            )
            if origin not in db_endpoints:
                success(f"Adding {origin} as a {vpn_name} target", indent=2)
                ep.etype_ref = vpn_etid
            else:
                error(f"{origin} already in the DB. Skipping", indent=2)
            e_dao.save(ep)

        progress(f"Elapsed time: {time.time() - start}", indent=2)
        success("Done")

    def validate(self, origin, vpn_type):
        vpn_name = EndpointType.get_name(vpn_type)
        enumerator = VpnEnumeratorFactory.from_name(vpn_name, origin, group="dummy")
        if enumerator is None:

            return False
        if enumerator is not None and enumerator.safe_validate():
            self.add_endpoint(origin, vpn_type)
            return True
        return False

    def parallel_validate(self, domains, **kwargs):
        d = kwargs.get("domain")
        for i in range(20):
            thread = DetectWorker()
            thread.threading_object = self
            thread.daemon = True
            thread.start()
        for domain in domains:
            e = kwargs.get("Endpoints", {}).get(domain)
            domain_info = create_additional_info(domain=d, endpoint=e)
            for vt in EndpointType.value_list():
                vpn_name = EndpointType.get_name(vt)
                enumerator = VpnEnumeratorFactory.from_name(vpn_name, domain, group="dummy")
                if not enumerator:
                    continue
                enumerator.setup(**domain_info)
                self.enqueue((enumerator, vt))
        self.wait_threads()

    def parallel_validate_office(self, domains, **kwargs):
        d = kwargs.get("domain")

        for i in range(20):
            thread = DetectWorker()
            thread.threading_object = self
            thread.daemon = True
            thread.start()
        for domain in domains:
            e = kwargs.get("endpoints", {}).get(domain)
            domain_info = create_additional_info(domain=d, endpoint=e)
            for vt in EndpointType.value_list():
                vpn_name = EndpointType.get_name(vt)
                enumerator = OfficeEnumeratorFactory.from_name(vpn_name, domain, group="dummy")
                if not enumerator:
                    continue
                enumerator.setup(**domain_info)
                self.enqueue((enumerator, vt))
        self.wait_threads()

    def parallel_validate2(self, domains):
        threads = []
        self.lock.acquire()
        for origin in domains:
            for vt in EndpointType.value_list():
                threads.append(threading.Thread(target=self.validate, args=(origin, vt)))
        for t in threads:
            t.daemon = True
            t.start()
        for t in threads:
            t.join()
