import html
import inspect
import re
import threading
from binascii import hexlify
from tempfile import NamedTemporaryFile
from typing import Union

from colorama import Fore
from requests import Response
from yaml import load

from enumerators.interfaces.ignite import Ignite
from utils.utils import get_project_root, info, highlight, warning, error, progress, success, std_soup

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class Nuclei(Ignite):

    def __init__(self):
        super().__init__()
        self.templates_directory = self.config.get("NUCLEI", "templates_directory")
        self.templates = []
        self.current_template = ""
        self.action = "detect"
        self.base_url = None
        self.lock = None
        self.verbose = int(self.config.get("NUCLEI", "verbose")) == 1
        self.debug = int(self.config.get("NUCLEI", "debug")) == 1
        self.caller = "vpn" if inspect.stack()[2][0].f_code.co_filename.find("vpn") != -1 else "office"
        # print([x[0].f_code.co_filename for x in inspect.stack()])
        self.map = {}

    def setup(self, **kwargs):
        if "lock" in kwargs.keys():
            self.lock = kwargs.get("lock")
        if "action" in kwargs.keys():
            action = kwargs.get("action")
            if self.validate_action(action):
                self.action = action
        if "target" in kwargs.keys():
            self.base_url = kwargs.get("target")
        if "class" in kwargs.keys():
            name = kwargs.get("class")
            name = re.search(r'[A-Z][a-z0-9]+', name).group(0)
            name = name.lower()
            self.load(name)
        if "map" in kwargs.keys():
            _map = kwargs.get("map")
            if isinstance(_map, dict):
                self.map = _map

    def validate_action(self, action):
        p = get_project_root().joinpath(self.templates_directory, action)
        if not p.exists():
            return False
        return True

    def load(self, name):
        try:
            p = get_project_root().joinpath(self.templates_directory, self.action, self.caller, name)
            if not p.exists():
                return None
            for f in p.glob("*.yaml"):
                with open(f, "r") as stream:
                    self.templates.append(load(stream.read(), Loader=Loader))
        except Exception as e:
            warning(e)

    def __update_body(self, body):
        if not self.map or not body:
            return body
        for k, v in self.map.items():
            body = body.replace(f"{{{k}}}", v)

    def __update_headers(self):
        if not self.map:
            return
        for k, v in self.map.items():
            for h in self.session.headers.keys():
                self.session.headers[h] = self.session.headers[h].replace(f"{{{k}}}", v)

    def __dsl_search_safe(self, dsl, response: Response):
        import ast
        import pure_eval
        e = pure_eval.Evaluator({"resp": response})
        tree = ast.parse(f"({dsl})".replace("||", " or ").replace("&&", " and "))
        for node, value in e.find_expressions(tree):
            return value

    def __dsl_search(self, dsl, resp: Response):
        import json
        import base64
        import hashlib
        import binascii
        from base64 import b64decode
        from utils.ntlmdecoder import extract_owa_domain
        soup = std_soup(resp.text)
        if isinstance(dsl, list):
            dsl = " ".join(dsl)
        try:
            return eval(dsl)
        except Exception as e:
            print(e)
            return None

    def request(self, url, method="GET", headers=None, body=None,
                follow_redirects=True, max_redirects=None) -> Union[Response, Exception]:
        body = self.__update_body(body)
        self.__update_headers()
        if max_redirects:
            self.session.max_redirects = max_redirects
        try:
            if headers:
                self.session.headers.update(headers)
            if method == "GET":
                return self.session.get(url, allow_redirects=follow_redirects)
                # info(f"{url}: {res.status_code} - {res.text} - follow {follow_redirects}", lock=self.lock)
            elif method == "HEAD":
                return self.session.head(url, allow_redirects=follow_redirects)
            elif method == "POST":
                return self.session.post(url, data=body, allow_redirects=follow_redirects)
            elif method == "PUT":
                return self.session.put(url, data=body, allow_redirects=follow_redirects)
            elif method == "DELETE":
                return self.session.delete(url, data=body, allow_redirects=follow_redirects)
            else:
                return Exception("Vortex Exception: Invalid HTTP method")
        except Exception as e:
            return Exception(f"Vortex Exception: {e}")

    def extract(self, target: Response, mtype, where, what: list, name=None, group: int = 0, internal=False):
        if not mtype or mtype not in ["regex", "kval", "json", "dsl", "xpath"]:
            return False

        if isinstance(what, list) and len(what) >= 1:
            if self.verbose:
                warning("Only one value is supported for extraction. Using the first one")
            what = what[0]

        matching = None
        if mtype == "kval":
            for k, v in {**target.headers, **target.cookies}.items():
                if k.replace("-", "_") == what:
                    matching = v
                    break
        elif mtype == "json":
            try:
                from plumbum.cmd import jq
                file = NamedTemporaryFile(suffix=".json", delete=False)
                file.write(target.text)
                content = (jq[what, file.name]).strip()
                matching = content
            except ImportError:
                warning("JQ might not be installed on your system. Please install it to use JSON extractor")
                return False
        elif mtype == "xpath":
            import xml.etree.ElementTree as ET
            try:
                tree = ET.fromstring(target.text)
                matching = tree.find(what).text
            except Exception as e:
                error(f"Error while parsing XML: {e}")
                return False
        elif mtype == "regex" and where == "body":
            content = html.unescape(target.text)
            match = re.search(what, content)
            if match and group >= 0:
                matching = match.group(group)
            else:
                matching = re.findall(what, content)
        elif mtype == "regex" and where == "headers":
            content = "\n".join([f"{k}: {v}" for k, v in target.headers.items()])
            match = re.search(what, content)
            if match and group >= 0:
                matching = match.group(group)
            else:
                matching = re.findall(what, content)
        elif mtype == "dsl":
            matching = self.__dsl_search(what, target)

        if matching and isinstance(matching, list):
            matching = ",".join(matching)
        if name and matching:
            self.map[name] = matching
        if not internal and self.verbose:
            with threading.Lock():
                progress(f"[{highlight(self.current_template)}] Extracted: {highlight(matching, color=Fore.YELLOW)}", indent=2)
        return matching

    def match(self, target: Response, mtype, where, what: list, condition, negative: bool = False):
        if not mtype or mtype not in ["words", "regex", "binary", "status", "dsl", "size"]:
            return False
        if not condition or condition not in ["and", "or"]:
            condition = "or"

        matching = []
        if mtype == "status":
            matching = [target.status_code == int(w) for w in what]
        elif mtype == "size":
            matching = [target.headers.get("Content-Length") == int(w) for w in what]
        elif mtype == "words" and where == "body":
            content = target.text
            matching = [content.find(w) > -1 for w in what]
        elif mtype == "words" and where == "headers":
            content = "\n".join([f"{k}: {v}" for k, v in target.headers.items()])
            matching = [content.find(w) > -1 for w in what]
        elif mtype == "regex" and where == "body":
            content = target.text
            matching = [re.search(w, content) is not None for w in what]
        elif mtype == "regex" and where == "headers":
            content = "\n".join([f"{k}: {v}" for k, v in target.headers.items()])
            matching = [re.search(w, content) is not None for w in what]
        elif mtype == "binary" and where == "body":
            content = target.content
            content = hexlify(content).decode()
            matching = [content.find(w) > -1 for w in what]
        elif mtype == "dsl":
            matching = [self.__dsl_search(w, target) is not None for w in what]

        rv = False
        if condition == "and" and not negative:
            rv = len(matching) > 0 and all(matching)
        elif (condition == "or") or (condition == "and" and negative):
            rv = len(matching) > 0 and any(matching)
        else:
            rv = len(matching) > 0 and not any(matching)
        if rv and self.debug:
            with threading.Lock():
                success(f"[+] {target.url} - Matched: {what} in {where} with {mtype}", lock=self.lock)

        return rv

    def analyze(self, t) -> tuple:
        self.current_template = t.get("id")
        __requests = t.get("requests")

        for r in __requests:
            self.on_fire()
            method = r.get("method")
            url = r.get("path")[0].replace("{{BaseURL}}", self.base_url)
            info(f"Nuclei Template: {highlight('`' + t.get('id') + '`'):40} - URL: {url}", lock=self.lock)
            headers = r.get("headers")
            body = r.get("body")
            follow_redirects = r.get("host-redirects")
            max_redirects = r.get("max-redirects")
            res = self.request(url, method, headers, body, follow_redirects, max_redirects)
            if isinstance(res, Exception) and str(res).startswith("Vortex Exception"):
                if self.debug:
                    warning(f"Exception: {res}")
                return False, res

            # Matchers
            __matchers = r.get("matchers") if r.get("matchers") else []
            matches = []

            # Extractors
            __extractors = r.get("extractors") if r.get("extractors") else []
            extracts = []

            # Matchers can be joined by "and" or "or" condition
            __matchers_global_condition = r.get("matchers-condition")
            if not __matchers_global_condition or __matchers_global_condition not in ["and", "or"]:
                __matchers_global_condition = "or"
            for m in __matchers:
                mtype = m.get("type") if m.get("type") != "word" else "words"  # A plural here, seriously!?!
                where = m.get("part")
                what = m.get(mtype)
                condition = m.get("condition")
                """
                info(f"Mtype: {mtype} "
                     f"- Where: {where} "
                     f"- What: {what} "
                     f"- Condition: {condition} "
                     f"- Global: {__matchers_global_condition}",
                     lock=self.lock)
                """
                matches.append(self.match(res, mtype, where, what, condition))

            for m in __extractors:
                mtype = m.get("type")
                where = m.get("part", None)
                what = m.get(mtype)
                name = m.get("name")
                internal = m.get("internal", False)
                group = int(m.get("group", 0))
                extracts.append(self.extract(res, mtype, where, what, name, group, internal=internal))

            # If all matchers are true, and the matchers are in AND, then the template is a match
            if len(matches) > 0 and all(matches) and __matchers_global_condition == "and":
                return True, res
            # If any of the matchers are true, and the matchers are in OR, then the template is a match
            elif len(matches) > 0 and any(matches) and __matchers_global_condition == "or":
                return True, res
            # Otherwise, the template is not a match
            else:
                return False, res

    def run(self):
        for t in self.templates:
            r = self.analyze(t)
            if r[0]:
                return r
        return False, None
