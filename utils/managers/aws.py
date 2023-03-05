import configparser
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Union, Any

import boto3

from db.dao.aws_api import AwsApiDao
from utils.managers.fire import FireProx
from utils.utils import *
from multiprocessing import Process, Queue
from timeit import default_timer as timer
from datetime import timedelta


class AWSManager:
    def __init__(self, **kwargs):
        self.client = boto3.client('ec2')
        self.credentials = {"accounts": []}
        self.regions = [
            "us-east-2", "us-east-1", "us-west-1", "us-west-2", "eu-west-3",
            "ap-northeast-1", "ap-northeast-2", "ap-south-1",
            "ap-southeast-1", "ap-southeast-2", "ca-central-1",
            "eu-central-1", "eu-west-1", "eu-west-2", "sa-east-1",
        ]
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(str(get_project_root().joinpath("config", "aws.config")))
        self.globals = configparser.ConfigParser(allow_no_value=True,
                                                 interpolation=configparser.ExtendedInterpolation())
        self.globals.read(str(get_project_root().joinpath("config", "config.ini")))
        self.thread_count = int(self.globals.get("NETWORK", "threads"))
        self.end_time = int(self.globals.get("OPERATION", "end_time"))

        self.dbh = kwargs.get("dbh")
        self.api_dao = None
        if self.dbh:
            self.api_dao = AwsApiDao(self.dbh)
        api_count = kwargs.get("napi") or kwargs.get("api_count")
        if api_count and isinstance(api_count, str):
            api_count = re.search(r"\d+", api_count)
            api_count = int(api_count.group(0))
        if api_count:
            self.thread_count = api_count

        profile = kwargs.get("profile")
        if not profile:
            profile = self.globals.get("AWS", "profile")
        self.access_key = None
        self.secret_access_key = None
        self.session_token = None
        self.profile_name = None

        self.load_credentials(profile)
        self.apis: list = []
        self.api_map = []
        self.fp: Union[FireProx, None] = None
        self.fire_prox()
        self.__timer = timer()
        self.lock = threading.BoundedSemaphore(self.thread_count)

    @property
    def time_elapsed(self):
        return timedelta(seconds=timer() - self.__timer)

    def fire_prox(self, args: dict = None):
        if args is None:
            args = {"command": "list", "region": random.choice(self.regions)}
        fp_args, help_str = self.__fire_prox_args(**args)
        self.fp = FireProx(fp_args, help_str)

    def fp_set_region(self, region):
        if region is not None and region in self.regions:
            self.fp.region = region
            self.fp.reload_client()

    def fp_set_api(self, api: Union[int, dict, None]):
        _id = self.__extract_api_id(api)
        if not _id:
            return
        self.fp.api = _id

    def __extract_api_id(self, api: Union[str, dict, None]) -> Union[str, None]:
        _id = None
        if api is None:
            return None
        if isinstance(api, str) and api in self.regions:
            raise ValueError("Region passed instead of API ID")
        elif isinstance(api, str):
            return api
        elif isinstance(api, dict):
            if "api_gateway_id" in api.keys():
                return api.get("api_gateway_id")
            elif "id" in api.keys():
                return api.get("id")
            else:
                return None
        else:
            return None

    def fp_list_api(self):
        return self.fp.list_api()

    def fp_rm_api(self, api: Any = None):
        _id = self.__extract_api_id(api)
        if not _id:
            return
        rm_result = self.fp.delete_api(api_id=_id)
        if rm_result and self.api_dao is not None:
            # We remove the API from the DB only upon successful deletion
            self.api_dao.delete_by_id(_id)
        return rm_result

    def load_credentials(self, profile: str = None):
        if not profile:
            profile = "default"
        self.access_key = self.config.get(profile, "aws_access_key_id")
        self.secret_access_key = self.config.get(profile, "aws_secret_access_key")
        self.session_token = self.config.get(profile, "aws_session_token")
        self.profile_name = self.config.get(profile, "aws_profile_name")

    def load_apis(self, url, region=None):

        if self.thread_count > len(self.regions):
            info("Thread count over maximum, reducing to 15")
            self.thread_count = len(self.regions)

        info(f"Creating {self.thread_count} API Gateways for {url}")

        self.apis: list = []

        # slow but multithreading this causes errors in boto3 for some reason :(
        # I don't think so?
        for x in range(0, self.thread_count):
            reg = self.regions[x]
            if region is not None:
                reg = region
            t = threading.Thread(target=self.create_api, args=(reg, url.strip()))
            try:
                t.start()
                t.join()
            except Exception as e:
                error(f"Error creating API Gateway: {e}")

    def create_api(self, region, url):
        with self.lock:
            self.fp_set_region(region)
            resource_id, proxy_url = self.fp.create_api(url)
            api = {"api_gateway_id": resource_id, "url": url, "proxy_url": proxy_url, "region": region}
            if self.api_dao:
                self.api_dao.save_new(**api)
            self.apis.append(api)
            success(
                f"Created API - Region: {region} ID: ({api['api_gateway_id']}) - {api['proxy_url']} => {url}"
            )

    def list_urls(self, url=None):
        urls = []
        for api in self.apis:
            if not url or (url and url == api['url']):
                urls.append(api['proxy_url'])
        return urls

    def __fire_prox_args(self, command, region, url=None, api_id=None):
        args = {
            "access_key": self.access_key,
            "secret_access_key": self.secret_access_key,
            "url": url,
            "command": command,
            "region": region,
            "api_id": api_id,
            "profile_name": self.profile_name,
            "session_token": self.session_token
        }

        help_str = "Error, inputs cause error."

        return args, help_str

    def display_stats(self, start=True):
        if start:
            info(f"Total Regions Available: {len(self.regions)}")
            info(f"Total API Gateways: {len(self.apis)}")

        if self.end_time and not start:
            info(f"End Time: {self.end_time}")
            info(f"Total Execution: {self.time_elapsed} seconds")

    def list_api_regions(self, region, show=True):
        region_apis = []
        with self.lock:
            self.fp_set_region(region)
            active_apis = self.fp_list_api()
            if show:
                info(f"Region: {region:15} - total APIs: {len(active_apis)}")

            if len(active_apis) != 0:
                for api in active_apis:
                    if show:
                        progress(
                            f"API Info --  ID: {api['id']}, "
                            f"Name: {api['name']}, "
                            f"Created Date: {api['createdDate']}"
                        )
                    if api["name"].find("fireprox") > -1:
                        region_apis.append(api)
                        self.apis.append(api)
            return region, region_apis

    def list_apis(self, show=True) -> dict:
        fireprox_apis = {}
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            for result in executor.map(self.list_api_regions, self.regions):
                fireprox_apis[result[0]] = result[1]

        self.api_map = fireprox_apis
        seen = []
        unique_apis = []
        for api in self.apis:
            if api.get("id") not in seen:
                unique_apis.append(api)
                seen.append(api.get("id"))
        self.apis = unique_apis
        return fireprox_apis

    def list_apis_offline(self) -> dict:
        apis = {}
        if not self.api_dao:
            return apis
        info(f"Listing API in the DB:")
        for region in self.regions:
            apis = self.api_dao.find_by_region(region)
            info(f"Region: {region:15} - total APIs: {len(apis)}")
            for api in apis:
                progress(f"API: {api.api_id} - {api.proxy_url} => {api.url}")

    def delete_apis_offline(self) -> dict:
        apis = {}
        if not self.api_dao:
            return apis
        info(f"Listing API in the DB:")
        for region in self.regions:
            with self.lock:
                self.fp_set_region(region)
                apis = self.api_dao.find_by_region(region)
                info(f"Region: {region:15} - total APIs: {len(apis)}")
                for api in apis:
                    progress(f"[DELETE] API: {api.api_id} - {api.proxy_url} => {api.url}")
                    self.fp_rm_api(api)

    def fp_locate_api(self, region, api_id) -> bool:
        self.fp_set_region(region)
        for _api in self.fp_list_api():
            if _api["id"] == api_id:
                success(f"API found in region {region}")
                self.fp_set_api(api_id)
                return True
        return False

    def destroy_in_region(self, region):
        info(f"Destroying all APIs in {region}...")
        self.fp_set_region(region)
        apis = self.fp_list_api()
        n = self.parallel_destroy_apis(apis)
        success(f"Destroyed {n} APIs in {region}")

    def destroy_in_region_in_session(self, region, apis):
        info(f"Destroying all APIs in {region}...")
        self.fp_set_region(region)
        n = self.parallel_destroy_apis(apis)
        success(f"Destroyed {n} APIs in {region}")

    def destroy_single_api(self, api: Union[str, dict, None]):
        info("Destroying single API, locating region...")
        for region in self.regions:
            if self.fp_locate_api(region, api):
                self.fp_rm_api(api)
            else:
                error("API not found")

    def destroy_api(self, api: int = None):
        debug(f"Destroying API: {api} in region {self.fp.region}...", indent=2)
        time.sleep(random.uniform(0.1, 0.3))
        with self.lock:
            return self.fp_rm_api(api)

    def parallel_destroy_apis(self, apis: list = None):
        to_delete = self.fp_list_api() if not apis else apis
        just_ids = [self.__extract_api_id(api) for api in to_delete]
        with ThreadPoolExecutor(max_workers=max(10, len(apis))) as executor:
            results = executor.map(self.destroy_api, just_ids)
        return sum(results)

    def clear_all_apis(self):
        if len(self.apis) == 0:
            self.list_apis(show=False)
        info("Clearing APIs for all regions")
        for region in self.regions:
            self.destroy_in_region(region)
        info("Fetching remaining APIs...")
        apis = self.list_apis()
        for region in apis.keys():
            if len(apis[region]) > 0:
                progress(f"Region: {region} - APIs: {len(apis[region])}")

    def clear_all_apis_in_session(self):
        info("Clearing registered APIs for all regions")
        self.delete_apis_offline()
        info("Fetching remaining APIs...")
        self.list_apis_offline()


