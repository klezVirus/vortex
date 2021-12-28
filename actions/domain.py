import queue
import threading
import timeit
from _queue import Empty

from db.dao.endpoint import EndpointDao
from db.enums.types import EndpointType
from db.models.endpoint import Endpoint
from enumerators.factories import VpnEnumeratorFactory
from enumerators.parallel import DetectWorker
from lib.Sublist3r.sublist3r import main, portscan

from actions.action import Action
from utils.utils import *


class Domain(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = ["enum", "brute"]
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
        if domain is None:
            error("Domain field is required")
            info("Please provide a target domain")
            domain = self.wait_for_input()

        e_dao = EndpointDao(handler=self.dbh)

        db_endpoints = [e.target for e in e_dao.list_all()]

        brute = False
        start = time.time()
        if command == "enum":
            info("Starting subdomain passive enumeration")
        elif command == "brute":
            info("Starting subdomain bruteforce... can require some time")
            brute = True
        else:
            error("Unknown command")
            exit(1)

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
        progress(f"Found {len(subdomains)} subdomains", indent=2)
        self.save(subdomains, self.__temp_domains)
        debug(f"Elapsed time: {time.time() - start}", indent=2)
        info("Enumerating potential VPN endpoints (HTTPS on 443, 10443)")
        scanner = portscan(subdomains, ports=[443, 10443])
        scanner.run()
        origins = scanner.origins
        progress(f"Found {len(origins)} hosts running an SSL webserver", indent=2)
        self.save(origins, self.__temp_origins)
        debug(f"Elapsed time: {time.time() - start}", indent=2)
        info(f"Trying to detect hosts with VPN web-login")
        self.parallel_validate(domains=origins)
        progress(f"Found {len(self.endpoints)} hosts with a VPN web login", indent=2)
        debug(f"Elapsed time: {time.time() - start}", indent=2)
        info(f"Updating DB...")
        for endpoint in self.endpoints:
            vpn_name = EndpointType.get_name(endpoint['endpoint_type'])
            origin = endpoint['endpoint']
            if origin not in db_endpoints:
                success(f"Adding {origin} as a {vpn_name} target", indent=2)
                ep = Endpoint(eid=0, target=origin, endpoint_type=endpoint["endpoint_type"])
                e_dao.save(ep)
            else:
                error(f"{origin} already in the DB. Skipping", indent=2)

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

    def parallel_validate(self, domains):
        for i in range(20):
            thread = DetectWorker()
            thread.threading_object = self
            thread.daemon = True
            thread.start()
        for domain in domains:
            for vt in EndpointType.value_list():
                vpn_name = EndpointType.get_name(vt)
                enumerator = VpnEnumeratorFactory.from_name(vpn_name, domain, group="dummy")
                if not enumerator:
                    continue
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
