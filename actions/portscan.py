import queue

from actions.subdomain import Subdomain
from lib.Sublist3r.sublist3r import PortScanner

from actions.action import Action
from utils.utils import *


class Portscan(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = {
            "from_db": ["domain"],
            "custom": ["url"]
        }
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
        _filter = kwargs.get("filter")
        _no_validate = kwargs.get("no_validate")
        ports = kwargs.get("ports")
        domain = kwargs.get("domain")
        target = kwargs.get("url")


        start = time.time()

        if command == "from_db":
            oracle = self.dbms.create_empty_oracle(domain)
            info(f"Starting portscan against {highlight(domain)}")
            db_domains = self.dbms.get_subdomains(domain, dfilter=_filter)

            for d in db_domains:
                oracle["subdomains"] = {d.name: d.additional_info_json}

            subdomains = [x.name for x in db_domains]
            progress(f"Found {len(subdomains)} subdomains in the database")
        elif command == "custom":
            target, port = extract_target_port(target)
            subdomains = [target]
            if port:
                ports = [port]
            # We do some background checks on the target
            if not self.dbms.exists_domain(target):
                info(f"Target not found in the database, starting domain check")

                fmt = self.dbms.get_email_format(target)
                dd = Subdomain.resolve(target)
                dt = Subdomain.takeover((target, dd[1]))
                self.dbms.save_new_domain(
                    did=0,
                    name=target,
                    email_format=fmt,
                    dns=dd[1],
                    frontable=dd[2],
                    takeover=dt[1],
                    additional_info=None
                )

        else:
            error("Unknown command")
            return
        if not ports:
            ports = self.config.get("SCANNER", "ports")

        if not ports:
            ports = [443, 1443, 8443, 10443]
        elif isinstance(ports, str):
            ports = [int(p.strip()) for p in ports.split(",") if validate_port(p.strip())]

        origins = self.dbms.diff_origins(subdomains, ports)

        info(f"Starting portscan against {highlight(target)}")

        if len(origins) > 0:
            info(f"Enumerating potential VPN/MS endpoints (HTTP[S] on {', '.join([str(x) for x in ports])})")
            scanner = PortScanner(origins=origins)
            scanner.run()
            info(f"Checking for SSL services (HTTPS) ...")
            scanner.run_ssl()

            origins_up = origins = scanner.origins
            origins_down = [o for o in origins if o not in origins_up]
            origins_ssl = [x for x in scanner.ssl_origins.keys() if scanner.ssl_origins.get(x)["ssl"]]

            progress(f"Found {len(origins_up)} origins hosting a running service")
            self.dbms.save_origins(
                origins_up, origins_down, origins_ssl
            )
            self.save(origins, self.__temp_origins)
        else:
            info(f"All origins were already found in the DB. Skipping port scan.")

        progress(f"Elapsed time: {time.time() - start}")
        success("Done")

