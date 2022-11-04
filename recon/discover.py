import configparser
import re
import json
import socket
import logging
import requests
import dns.resolver
import xmltodict
from requests import request

from utils.ntlmdecoder import ntlmdecode
try:
    from utils.utils import *
except:
    from utils import *

from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from urllib.parse import urlparse, urlunparse

suggestion_regexes = (
    re.compile(r'[^\d\W_-]+', re.I),
    re.compile(r'[^\W_-]+', re.I),
    re.compile(r'[^\d\W]+', re.I),
    re.compile(r'[^\W]+', re.I),
)


class DomainDiscovery:

    def __init__(self, domain):
        self.domain = ''.join(str(domain).split()).strip('/')

        self.dns_records = {}
        self._mx_records = None
        self._txt_records = None
        self._autodiscover = None
        self._userrealm = None
        self._openid_configuration = None
        self._msol_domains = None
        self._owa = None
        self._onedrive_tenant_names = None
        self.tenant_names = []
        self.recon_data = None
        self.session = requests.session()
        self.session.verify = False
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Te": "trailers",
            "Connection": "close"
        }
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(str(get_project_root().joinpath("config", "config.ini")))
        if int(self.config.get("NETWORK", "enabled")) != 0:
            proxy = self.config.get("NETWORK", "proxy")
            self.toggle_proxy(proxy=proxy)

        self.session.max_redirects = 5
        self.debug = int(self.config.get("DEBUG", "developer")) > 0

    def toggle_proxy(self, proxy=None):
        if self.session.proxies is not None and proxy is None:
            self.session.proxies = None
        else:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }

    def recon(self):

        self.printjson(self.get_mx_records())
        self.printjson(self.get_txt_records())

        openid_configuration = self.get_openid_configuration()
        self.printjson(openid_configuration)
        authorization_endpoint = openid_configuration.get('authorization_endpoint', '')
        uuid_regex = re.compile(r'[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}')
        matches = uuid_regex.findall(authorization_endpoint)
        if matches:
            success(f'Tenant ID: "{matches[0]}"')

        self.printjson(self.get_userrealm())
        self.printjson(self.autodiscover())
        self.owa()

        msoldomains = self.get_msol_domains()
        if msoldomains:
            self.printjson(msoldomains)
        self.get_onedrive_tenant_names()

    @staticmethod
    def printjson(j):
        if isinstance(j, list):
            j = {"data": j}

        if j:
            success(f'\n{json.dumps(j, indent=2)}')
        else:
            warning('No results.')

    def get_openid_configuration(self):

        if self._openid_configuration is None:
            url = f'https://login.windows.net/{self.domain}/.well-known/openid-configuration'
            info(f'Checking OpenID configuration at {url}')

            content = None
            try:
                content = self.session.get(url=url).json()
            except Exception as e:
                pass
            self._openid_configuration = content if content else {}

        return self._openid_configuration

    def get_userrealm(self):

        try:
            if self._userrealm is None:
                url = f'https://login.microsoftonline.com/getuserrealm.srf?login=test@{self.domain}'
                info(f'Checking user realm at {url}')

                content = None
                try:
                    content = self.session.get(url=url).json()
                except Exception as e:
                    pass
                self._userrealm = content
        except:
            pass
        return self._userrealm

    def get_mx_records(self):
        try:
            if self._mx_records is None:
                info(f'Checking MX records for {self.domain}')
                mx_records = []
                with suppress(Exception):
                    for x in dns.resolver.resolve(self.domain, 'MX'):
                        mx_records.append(x.to_text())
                self._mx_records = mx_records
        except:
            pass
        return self._mx_records

    def get_txt_records(self):
        try:
            if self._txt_records is None:
                info(f'Checking TXT records for {self.domain}')
                txt_records = []
                with suppress(Exception):
                    for x in dns.resolver.resolve(self.domain, 'TXT'):
                        txt_records.append(x.to_text())
                self._txt_records = txt_records
        except:
            pass
        return self._txt_records

    def get_a_records(self):
        try:
            records = []
            with suppress(Exception):
                for x in dns.resolver.resolve(self.domain, 'A'):
                    records.append(x.to_text())
            return records
        except:
            return None

    def get_aaaa_records(self):
        try:
            records = []
            with suppress(Exception):
                for x in dns.resolver.resolve(self.domain, 'AAAA'):
                    records.append(x.to_text())
            return records
        except:
            return None

    def autodiscover(self):

        if self._autodiscover is None:
            url = f'https://outlook.office365.com/autodiscover/autodiscover.json/v1.0/test@{self.domain}?Protocol=Autodiscoverv1'
            info(f'Checking autodiscover info at {url}')
            content = dict()

            try:
                r = self.session.get(url=url)
                content = r.json()
            except json.JSONDecodeError:
                pass
            except:
                pass
            self._autodiscover = content

        return self._autodiscover

    def get_msol_domains(self):

        try:
            if self._msol_domains is None:

                url = 'https://autodiscover-s.outlook.com/autodiscover/autodiscover.svc'

                data = f'''<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:exm="http://schemas.microsoft.com/exchange/services/2006/messages" xmlns:ext="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <soap:Header>
                <a:Action soap:mustUnderstand="1">http://schemas.microsoft.com/exchange/2010/Autodiscover/Autodiscover/GetFederationInformation</a:Action>
                <a:To soap:mustUnderstand="1">https://autodiscover-s.outlook.com/autodiscover/autodiscover.svc</a:To>
                <a:ReplyTo>
                    <a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
                </a:ReplyTo>
            </soap:Header>
            <soap:Body>
                <GetFederationInformationRequestMessage xmlns="http://schemas.microsoft.com/exchange/2010/Autodiscover">
                    <Request>
                        <Domain>{self.domain}</Domain>
                    </Request>
                </GetFederationInformationRequestMessage>
            </soap:Body>
        </soap:Envelope>'''

                headers = {
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': '"http://schemas.microsoft.com/exchange/2010/Autodiscover/Autodiscover/GetFederationInformation"',
                    'User-Agent': 'AutodiscoverClient',
                    'Accept-Encoding': 'identity'
                }

                info(f'Retrieving tenant domains at {url}')

                response = requests.post(
                    url,
                    headers=headers,
                    data=data
                )

                x = xmltodict.parse(response.text)
                domains = x.get(
                    "s:Envelope", {}
                ).get(
                    "s:Body", {}
                ).get(
                    "GetFederationInformationResponseMessage", {}
                ).get(
                    "Response", {}
                ).get(
                    "Domains", {}
                ).get("Domain")

                if not domains:
                    domains = []

                for domain in domains:
                    # Check if this is "the initial" domain (tenantname)
                    if domain.lower().endswith('.onmicrosoft.com'):
                        self.tenant_names.append(domain.split('.')[0])

                if self.tenant_names:
                    success(f'Found tenant names: "{", ".join(self.tenant_names)}"')

                if domains and len(domains) > 0:
                    success(f'Found {len(domains):,} domains under tenant!')

                self._msol_domains = domains
        except:
            pass
        return self._msol_domains

    def get_onedrive_tenant_names(self):

        try:

            if self._onedrive_tenant_names is None:

                self.get_msol_domains()

                if not self.tenant_names:
                    return []

                self._onedrive_tenant_names = []

                info(f'Checking OneDrive instances')

                for tenantname in self.tenant_names:

                    url = f'https://{tenantname}-my.sharepoint.com/personal/TESTUSER_{"_".join(self.domain.split("."))}/_layouts/15/onedrive.aspx'

                    status_code = 0
                    try:
                        r = self.session.head(url=url)
                        if r:
                            success(f'Tenant "{tenantname}" confirmed via OneDrive: {url}')
                            self._onedrive_tenant_names.append(tenantname)
                    except Exception as e:
                        warning(f'Hosted OneDrive instance for "{tenantname}" does not exist')
                self._onedrive_tenant_names = list(set(self._onedrive_tenant_names))
        except:
            pass
        return self._onedrive_tenant_names

    def owa(self):

        if self._owa is None:

            info('Attempting to discover OWA instances')

            owas = set()

            schemes = [
                'http://',
                'https://'
            ]

            urls = [
                f'autodiscover.{self.domain}/autodiscover/autodiscover.xml',
                f'exchange.{self.domain}/autodiscover/autodiscover.xml',
                f'webmail.{self.domain}/autodiscover/autodiscover.xml',
                f'email.{self.domain}/autodiscover/autodiscover.xml',
                f'mail.{self.domain}/autodiscover/autodiscover.xml',
                f'owa.{self.domain}/autodiscover/autodiscover.xml',
                f'mx.{self.domain}/autodiscover/autodiscover.xml',
                f'{self.domain}/autodiscover/autodiscover.xml',
            ]
            urls += [f'{mx.split()[-1].strip(".")}/autodiscover/autodiscover.xml' for mx in self._mx_records]
            urls = list(set(urls))

            headers = {
                'Content-Type': 'text/xml'
            }

            for scheme in schemes:
                for u in urls:
                    url = f'{scheme}{u}'
                    r = self.session.get(
                        url=url,
                        headers=headers,
                    )
                    response_headers = r.headers
                    if 'x-owa-version' in response_headers.keys() or \
                            'NTLM' in response_headers.get('www-authenticate'):
                        success(f'Found OWA at {r.url}')
                        self.owa_internal_domain(
                            url=r.request.url
                        )
                        owas.add(r.request.url)

            self._owa = list(owas)

        return self._owa

    def owa_internal_domain(self, url=None):

        if url is None:
            url = f'https://{self.domain}/autodiscover/autodiscover.xml'

        debug(f'Trying to extract internal domain via NTLM from {url}')

        juicy_endpoints = [
            'aspnet_client',
            'autodiscover',
            'autodiscover/autodiscover.xml',
            'ecp',
            'ews',
            'ews/exchange.asmx',
            'ews/services.wsdl',
            'exchange',
            'microsoft-server-activesync',
            'microsoft-server-activesync/default.eas',
            'oab',
            'owa',
            'powershell',
            'rpc',
        ]

        urls = {url, }
        parsed_url = urlparse(url)
        base_url = urlunparse(parsed_url._replace(query='', path=''))
        for endpoint in juicy_endpoints:
            urls.add(f'{base_url}/{endpoint}'.lower())

        netbios_domain = ''
        for url in urls:
            r = self.session.post(url, headers={
                    'Authorization': 'NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw=='
                })
            ntlm_info = {}
            www_auth = getattr(r, 'headers', {}).get('WWW-Authenticate', '')
            if www_auth:
                try:
                    ntlm_info = ntlmdecode(www_auth)
                except Exception as e:
                    debug(f'Failed to extract NTLM domain: {e}')
            if ntlm_info:
                netbios_domain = ntlm_info.get(
                    'DNS_Domain_name',
                    ntlm_info.get(
                        'DNS_Tree_Name',
                        ntlm_info.get('NetBIOS_Domain_Name', '')
                    )
                )
                success(f'Found internal domain via NTLM: "{netbios_domain}"')
                ntlm_info.pop('Timestamp', '')
                self.printjson(ntlm_info)
                break
        return netbios_domain

