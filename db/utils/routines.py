import re
from typing import Union

from db.dao.aws_api import AwsApiDao
from db.dao.domain import DomainDao
from db.dao.endpoint import EndpointDao
from db.dao.etype import EtypeDao
from db.dao.leak import LeakDao
from db.dao.login import LoginDao
from db.dao.origin import OriginDao
from db.dao.profile import ProfileDao
from db.dao.user import UserDao
from db.handler import DBHandler
from db.models.domain import Domain
from db.models.endpoint import Endpoint
from db.models.leak import Leak
from db.models.origin import Origin
from db.models.user import User
from enumerators.search.structures.unified_user_data import UnifiedUserData, UnifiedUserDataList
from utils.utils import extract_domain, is_subdomain, validate_target_port, create_additional_info, error


class Routine:
    def __init__(self, dbh: DBHandler):
        self.dbh = dbh
        self.dbh.connect()
        self.endpoint_dao = EndpointDao(handler=self.dbh)
        self.etype_dao = EtypeDao(handler=self.dbh)
        self.domain_dao = DomainDao(handler=self.dbh)
        self.origin_dao = OriginDao(handler=self.dbh)
        self.leak_dao = LeakDao(handler=self.dbh)
        self.login_dao = LoginDao(handler=self.dbh)
        self.user_dao = UserDao(handler=self.dbh)
        self.profile_dao = ProfileDao(handler=self.dbh)
        self.aws_api_dao = AwsApiDao(handler=self.dbh)

    def create_empty_oracle(self, domain):
        m_domain_obj = self.domain_dao.find_by_name(extract_domain(domain))
        if not m_domain_obj:
            return None
        return {
            "domain": m_domain_obj.additional_info_json,
            "subdomains": {},
            "endpoints": {}
        }

    def create_additional_info(self, domain: Union[Domain, str, None] = None, subdomain: Union[Domain, str, None] = None,
                               endpoint: Union[Endpoint, str, None] = None):
        if isinstance(domain, str):
            domain = self.domain_dao.find_by_name(extract_domain(domain))
        if isinstance(subdomain, str):
            subdomain = self.domain_dao.find_by_name(subdomain)
        if isinstance(endpoint, str):
            subdomain = self.endpoint_dao.find_by_name(endpoint)
        return create_additional_info(domain, subdomain, endpoint)

    def get_domain(self, domain):
        return self.domain_dao.find_by_name(domain)

    def get_subdomains(self, domain, dfilter=None):
        if is_subdomain(domain):
            db_domains = [self.domain_dao.find_by_name(domain)]
        elif domain == "*":
            # Get all registered endpoints
            db_domains = self.domain_dao.list_all()
        else:
            db_domains = self.domain_dao.find_by_name_like(domain)

        if dfilter:
            _fr = re.compile(dfilter, re.IGNORECASE)
            db_domains = [d for d in db_domains if _fr.search(d.name)]

        return db_domains

    def find_endpoint(self, origin, etype: Union[str, int]):
        potential_endpoints = self.get_endpoints(origin)
        if isinstance(etype, str):
            etype = self.etype_dao.find_by_name(etype)
        if isinstance(etype, int):
            etype = self.etype_dao.find_by_id(etype)
        for endpoint in potential_endpoints:
            if endpoint.etype == etype:
                return endpoint
        return None

    def get_etype_name(self, etype_id):
        return self.etype_dao.find_by_id(etype_id).name

    def get_endpoints(self, origin, dfilter=None):
        if is_subdomain(origin) and validate_target_port(origin):
            endpoints = [self.endpoint_dao.find_by_name(origin)]
        elif origin == "*":
            # Get all registered endpoints
            endpoints = self.endpoint_dao.list_all()
        else:
            endpoints = self.endpoint_dao.find_by_name_like(origin)

        if dfilter:
            _fr = re.compile(dfilter, re.IGNORECASE)
            endpoints = [e for e in endpoints if _fr.search(e.target)]

        return endpoints

    def get_users(self, dfilter=None):
        users = self.user_dao.list_all()
        if dfilter:
            _fr = re.compile(dfilter, re.IGNORECASE)
            users = [u for u in users if _fr.search(u.to_string())]
        return users

    def get_users_mails(self, dfilter=None):
        users = [u.email for u in self.user_dao.list_all()]
        if dfilter:
            _fr = re.compile(dfilter, re.IGNORECASE)
            users = [u for u in users if _fr.search(u)]
        return users

    def update_logins(self, logins: list, endpoint_id: int):
        updates = {"success": 0, "fail": 0}
        for login in logins:
            if not self.login_dao.exists(login["username"], login["password"], endpoint_id):
                self.login_dao.save_new(login["username"], login["password"], endpoint_id)
                updates["success"] += 1
            else:
                updates["fail"] += 1
        return updates

    def save_domain(self, domain: Domain):
        return self.domain_dao.save(domain)

    def save_new_domain(self, **kwargs):
        domain = Domain(**kwargs)
        return self.domain_dao.save(domain)

    def update_domain(self, domain: Domain):
        return self.domain_dao.update(domain)

    def clean_domain(self):
        """
        Remove all subdomains with no DNS information
        """
        return self.domain_dao.delete_if_no_dns()

    def save_origins(self, origins_up: list, origins_down: list, origin_ssl: list):
        for origin in origins_up:
            o = Origin(oid=0, host="", port="", up=True)
            o.origin = origin
            if origin in origin_ssl:
                o.ssl = True
            self.origin_dao.save(o)
        for origin in origins_down:
            o = Origin(oid=0, host="", port="", up=False)
            o.origin = origin
            self.origin_dao.save(o)

    def diff_origins(self, hosts: list, ports: list):
        combinations = [f"{h}:{p}" for h in hosts for p in ports]
        db_origins = [o.origin for o in self.origin_dao.list_all()]
        diff = [o for o in combinations if o not in db_origins]
        return diff

    def uncategorized_origins(self):
        db_origins = [o.origin for o in self.origin_dao.list_all()]
        db_endpoints = [e.target for e in self.endpoint_dao.list_all() if self.endpoint_dao.exists_categorised(e)]
        uncategorized = [o for o in db_origins if o not in db_endpoints]
        return uncategorized

    def db_aws_apis(self):
        return self.aws_api_dao.list_all()

    def db_origins(self, as_string=False, as_urls=False):
        if not as_string and not as_urls:
            return self.origin_dao.list_all()
        if as_string:
            return [o.origin for o in self.origin_dao.list_all()]
        if as_urls:
            for o in self.origin_dao.list_all():
                if o.ssl:
                    yield f"https://{o.origin}"
                else:
                    yield f"http://{o.origin}"

    def db_endpoints(self):
        return self.endpoint_dao.list_all()

    def db_domains(self):
        return self.domain_dao.list_all()

    def db_users(self):
        return self.user_dao.list_all()

    def db_profiles(self):
        return self.profile_dao.list_all()

    def db_logins(self):
        return self.login_dao.list_all()

    def db_leaks(self):
        return self.leak_dao.list_all()

    def db_etypes(self):
        return self.etype_dao.list_all()

    def get_etype_id(self, vpn_name):
        return self.etype_dao.find_by_name(vpn_name.upper()).etid

    def exists_domain(self, domain):
        return self.domain_dao.exists(domain)

    def get_email_format(self, origin):
        # Cascade approach to get email format
        # 1. Endpoint specific email format
        fmt = self.endpoint_dao.get_email_format(origin)
        if not fmt:
            # 2. Domain specific email format
            fmt = self.domain_dao.get_email_format(extract_domain(origin))
        if not fmt:
            # 3. Global email format
            fmt = self.dbh.get_email_format()
        return fmt

    def save_leak_from_uudata(self, uu: UnifiedUserData, uid: int):
        return Leak(
                        uid=uid,
                        leak_id=0,
                        password=uu.password,
                        address=uu.address,
                        phone=uu.phone,
                        hashed=uu.phash,
                        database=uu.db
                    )

    def save_users_from_uudata(self, uu: UnifiedUserDataList, domain: str):
        users, leaks = 0, 0
        for u in uu:
            try:
                u = u.normalize(domain)
                uid = self.save_user_from_uudata(u)
                users += 1
                if any([x not in [None, ""] for x in [u.password, u.phash, u.phone, u.host, u.db]]):
                    self.save_leak_from_uudata(u, uid)
                    leaks += 1
            except:
                pass
        return users, leaks

    def save_user_from_uudata(self, uu: UnifiedUserData):
        return self.user_dao.save(
            User(
                uid=0,
                email=uu.email,
                name=uu.name,
                role=uu.role
            )
        )

    def save_endpoint(self, endpoint: Endpoint):
        self.endpoint_dao.save(endpoint)

    def save_endpoints(self, endpoints: list):
        for endpoint in endpoints:
            if isinstance(endpoint, dict):
                _extract = endpoint.pop("nuclei-extracted", None)
                endpoint = Endpoint(**endpoint)
                if _extract:
                    endpoint.additional_info_json["nuclei"] = _extract
            if endpoint.email_format is None:
                endpoint.email_format = self.get_email_format(endpoint.target)

            self.endpoint_dao.save(endpoint)

    def delete_invalid_objects(self, objects):
        if not objects or not isinstance(objects, list) or len(objects) == 0:
            return
        if isinstance(objects[0], User):
            self.delete_user_objects(objects)
        elif isinstance(objects[0], Endpoint):
            self.delete_endpoint_objects(objects)
        elif isinstance(objects[0], Domain):
            self.delete_domain_objects(objects)

    def delete_user_objects(self, objects: list):
        for o in objects:
            try:
                self.user_dao.delete(o)
            except Exception as e:
                error(f"Exception: {e}")

    def delete_endpoint_objects(self, objects: list):
        for o in objects:
            try:
                self.endpoint_dao.delete(o)
            except Exception as e:
                error(f"Exception: {e}")

    def delete_domain_objects(self, objects: list):
        for o in objects:
            try:
                self.domain_dao.delete(o)
            except Exception as e:
                error(f"Exception: {e}")
