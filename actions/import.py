import csv
import os
import threading
import time

from actions.action import Action
from db.dao.endpoint import EndpointDao
from db.dao.user import UserDao
from db.models.endpoint import Endpoint
from db.models.leak import Leak
from db.models.user import User
from enumerators.factories import VpnEnumeratorFactory
from enumerators.parallel import DetectWorker
from utils.mashers.namemash import NameMasher
from utils.utils import info, error, progress, debug, success


class Import(Action):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.commands = {
            "blues": ["domain", "import_file"],
            "usernames": ["domain", "import_file"],
            "emails": ["import_file"],
            "pwndb": ["domain", "import_file"],
            "domains": ["domain", "import_file"],
            "origins": ["domain", "import_file"],
            "full-names": ["domain", "import_file"],
            "help": []
        }
        self.no_child_process = True

    def execute(self, **kwargs):
        self.dbh.connect()
        command = kwargs["command"]
        domain = kwargs["domain"]
        import_file = kwargs["import_file"]

        if command == "help":
            info("[--------------------------------------------------------------]")
            print(r""" The import utility allows you to import data from a file into the database.
 The file needs to be a file with the following format:
  - Linkedin2Username :     CSV (Name,Role,,)
  - Usernames         :     TXT (1 Username x line)
  - Emails            :     TXT (1 Email x line)
  - Pwndb             :     CSV (email, password, domain, date)          
            """)
            info("[--------------------------------------------------------------]")
            info("Available commands:")
            for k, v in self.commands.items():
                info(f"\t{k} {v}")
            exit(0)

        if not (import_file and os.path.isfile(import_file)):
            info("Please provide a file to import")
            import_file = self.wait_for_input()

        if not os.path.isfile(import_file):
            error("Import file not found")
            exit(1)

        dao = UserDao(handler=self.dbh)
        e_dao = EndpointDao(handler=self.dbh)
        db_endpoints = self.dbms.db_endpoints()

        if domain is None:
            error("Domain field is required")
            info("Please enter a target domain")
            domain = self.wait_for_input()

        info(f"Importing {command} form {import_file} into {domain}")


        if command == "blues":
            masher = NameMasher()
            mail_format = self.dbh.get_email_format()
            if not mail_format:
                masher.select_format()
                self.dbh.set_email_format(masher.fmt)
            else:
                masher.fmt = mail_format

            with open(import_file, encoding="utf-8", errors="replace") as imports:
                reader = csv.DictReader(imports)
                for row in reader:
                    name = row['Name']
                    role = row['Role']
                    if name.lower() == "linkedin member":
                        continue
                    username = masher.mash(name.split(" ")[0], name.split(" ")[-1])
                    email = f"{username}@{domain}"
                    user = User(uid=0, name=name, email=email, role=role)
                    dao.save(user)
        elif command == "full-names":
            masher = NameMasher()
            mail_format = self.dbh.get_email_format()
            if not mail_format:
                masher.select_format()
                self.dbh.set_email_format(masher.fmt)
            else:
                masher.fmt = mail_format

            with open(import_file, encoding="utf-8", errors="replace") as imports:
                for row in imports.readlines():
                    row = row.replace("'", "").replace("\n", "")
                    username = masher.mash(row.split(" ")[0], row.split(" ")[-1])
                    email = f"{username}@{domain}"
                    user = User(uid=0, name=row, email=email, role="")
                    dao.save(user)

        elif command == "usernames":
            with open(import_file) as imports:
                for username in imports:
                    email = f"{username}@{domain}"
                    user = User(uid=0, name="", email=email, role="")
                    dao.save(user)

        elif command == "emails":
            with open(import_file) as imports:
                for email in imports.readlines():
                    email = email.strip()
                    progress(f"Importing {email} into DB")
                    user = User(uid=0, name="", email=email, role="")
                    dao.save(user)

        elif command == "pwndb":
            users = {}
            with open(import_file) as imports:
                leak = None
                for line in imports:
                    if line.startswith("#"):
                        leak = line.split(",")[1].replace("\"", "").strip().split(" ")[0]
                        users[leak] = []
                    else:
                        cred = line.split(" ")[1].replace("\"", "").replace("\n", "").strip(" ()")
                        users[leak].append(cred)
            for u, leaks in users.items():
                if not u or u.strip() == "":
                    continue
                user = User(uid=0, name=None, email=u, role=None)
                user.leaks = [
                    Leak(leak_id=0,
                         password=leak,
                         uid=0,
                         database="pwndb",
                         hashed=None,
                         address=None,
                         phone=None
                         ) for leak in leaks]
                dao.save(user)

        elif command == "origins":
            start = time.time()
            users = {}
            with open(import_file) as imports:
                origins = imports.readlines()
                info(f"Trying to detect hosts with VPN web-login")
                self.parallel_validate(domains=origins)
                progress(f"Found {len(self.endpoints)} hosts with a VPN web login")
                debug(f"Elapsed time: {time.time() - start}")
                info(f"Updating DB...")

                for endpoint in self.endpoints:
                    vpn_name = self.dbms.get_etype_name(endpoint['endpoint_type'])
                    origin = endpoint['endpoint']
                    if origin not in db_endpoints:
                        success(f"Adding {origin} as a {vpn_name} target")
                        self.dbms.save_endpoint()

                        ep = Endpoint(
                            eid=0,
                            target=origin,
                            etype_ref=endpoint["endpoint_type"]
                        )
                        e_dao.save(ep)
                    else:
                        error(f"{origin} already in the DB. Skipping")

    def validate(self, origin, vpn_type):
        vpn_name = self.dbms.get_etype_name(vpn_type)
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
            for vt in self.dbms.db_etypes():
                vpn_name = vt.name
                enumerator = VpnEnumeratorFactory.from_name(vpn_name, domain, group="dummy")
                if not enumerator:
                    continue
                self.enqueue((enumerator, vt.etid))
        self.wait_threads()

    def parallel_validate2(self, domains):
        threads = []
        for origin in domains:
            for vt in self.dbms.db_etypes():
                threads.append(threading.Thread(target=self.validate, args=(origin, vt.etid)))
        for t in threads:
            t.daemon = True
            t.start()
        for t in threads:
            t.join()
