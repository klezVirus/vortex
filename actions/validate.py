import re
import threading
import time
import traceback

from actions.action import Action
from db.enums.types import EndpointType
from enumerators.factories import VpnEnumeratorFactory, OfficeEnumeratorFactory

from enumerators.parallel import DetectWorker
from utils.utils import success, error, info, progress, create_additional_info, debug, highlight
from validators.validator import Validator


class Validate(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = {
            "vpn": [""],
            "office": [""],
            "users": ["tech", "domain"]
        }

    def execute(self, **kwargs):
        domain = kwargs["domain"]
        command = kwargs["command"]
        _filter = kwargs["filter"]
        validator_name = kwargs["tech"]
        use_aws = kwargs.get("aws", False)

        if not _filter:
            _filter = re.compile(r".*")
        else:
            _filter = re.compile(_filter)
        # DB Routines
        oracle = self.dbms.create_empty_oracle(domain)
        if not oracle:
            error(f"Domain {highlight(domain)} does not exist.")
            info(f"Please run a subscan first.")
            return

        # Get all registered users
        users = self.dbms.db_users()

        # Keep trace of invalid objects
        invalid = []

        start = time.time()
        validator = None
        if command == "users":
            try:
                validator = Validator.from_name(validator_name)
                oracle["aws"] = kwargs["aws"]
                oracle["dbh"] = self.dbh
                validator.setup(**oracle)
                valid, invalid = self.parallel_user_validate(users=[u.email for u in users], validator=validator)
            except:
                error(f"Failed to validate users with {highlight(validator_name)}")
        elif command in ["vpn", "office"]:
            # We want to validate all origins that were not categorized yet
            origins = [x for x in self.dbms.db_origins(as_urls=True) if _filter.search(x)]

            if len(origins) == 0:
                error("No uncategorized origin found.")
                return
            try:
                if command == "vpn":
                    info(f"Trying to detect hosts with VPN web-login")
                    self.parallel_validate(domains=origins, **oracle)
                    progress(f"Found {len(self.endpoints)} hosts with a VPN web login")

                else:
                    info(f"Trying to detect hosts with MS on premise web-login")
                    self.parallel_validate_office(domains=origins, **oracle)
                    progress(f"Found {len(self.endpoints)} hosts with a MS on-premise web login")

                info("Updating endpoints in the database...")
                self.dbms.save_endpoints(self.endpoints)

                debug(f"Elapsed time: {time.time() - start}")
            except KeyboardInterrupt:
                exit(1)
            except Exception as e:
                error(f"Exception: {e}")

        if use_aws and validator:
            info("AWS Manager: Destroying APIs...")
            validator.aws_manager.clear_all_apis_in_session()

        if len(invalid) == 0:
            exit(1)
        else:
            info(f"Found {len(invalid)} invalid objects. If you'd like to delete them, specify `--delete`")
            if not kwargs.get("delete"):
                exit(1)
            self.dbms.delete_invalid_objects(invalid)

    def parallel_user_validate(self, users, validator, **kwargs):
        validator.setup(**kwargs)
        validator.parallel_validate(users)
        return validator.found, [u for u in users if u not in validator.found]

    def parallel_validate(self, domains, **kwargs):
        d = kwargs.get("domain")
        for i in range(20):
            thread = DetectWorker()
            thread.threading_object = self
            thread.daemon = True
            thread.start()
        lock = threading.Lock()
        for domain in domains:
            e = kwargs.get("endpoints", {}).get(domain)
            domain_info = create_additional_info(domain=d, endpoint=e)
            domain_info["lock"] = lock
            for vt in self.dbms.db_etypes():
                vpn_name = vt.name
                enumerator = VpnEnumeratorFactory.from_name(vpn_name, domain, group="dummy")
                if not enumerator:
                    continue
                enumerator.setup(**domain_info)
                self.enqueue((enumerator, vt.etid))
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
            for vt in self.dbms.db_etypes():
                vpn_name = vt.name
                enumerator = OfficeEnumeratorFactory.from_name(vpn_name, domain, group="dummy")
                if not enumerator:
                    continue
                enumerator.setup(**domain_info)
                self.enqueue((enumerator, vt.etid))
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

    def validate(self, origin, vpn_type):
        vpn_name = self.dbms.get_etype_name(vpn_type)
        enumerator = VpnEnumeratorFactory.from_name(vpn_name, origin, group="dummy")
        if enumerator is None:

            return False
        if enumerator is not None and enumerator.safe_validate():
            self.add_endpoint(origin, vpn_type)
            return True
        return False

    def validate_office(self, origin, vpn_type):
        vpn_name = self.dbms.get_etype_name(vpn_type)
        enumerator = OfficeEnumeratorFactory.from_name(vpn_name, origin, group="dummy")
        if enumerator is None:
            return False
        if enumerator is not None and enumerator.safe_validate():
            self.add_endpoint(origin, vpn_type)
            return True
        return False
