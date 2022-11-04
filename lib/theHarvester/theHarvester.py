#!/usr/bin/env python
# Standard Python libraries.
import argparse
import queue
import re
import sys
import threading
import time

# https://stackoverflow.com/questions/27981545/suppress-insecurerequestwarning-unverified-https-request-is-being-made-in-pytho#28002687
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Third party Python libraries.
import googlesearch  # noqa
import requests  # noqa

# Custom Python libraries.


class Worker(threading.Thread):
    """theHarvester class object"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.threading_object = None

    def run(self):
        """Start scraping for emails."""

        while True:
            # Grab URL off the queue.
            url = self.threading_object.queue.get()
            try:
                print("[+] Scraping any emails from: {}".format(url))

                headers = {"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html"}

                response = requests.get(url, proxies=self.threading_object.proxies, headers=headers, verify=False, timeout=self.threading_object.url_timeout)

                if response.status_code == 200:
                    response_text = response.text
                    for badchar in (">", ":", "=", "<", "/", "\\", ";", "&", "%3A", "%3D", "%3C"):
                        response_text = response_text.replace(badchar, " ")

                    emails = re.findall(r"[a-zA-Z0-9.-_]*@(?:[a-z0-9.-]*\.)?" + self.threading_object.__domain, response_text, re.I)
                    if emails:
                        for e in emails:
                            self.threading_object.all_emails.append(e)

            except Exception as e:
                print("[-] Exception: {}".format(e))

            self.threading_object.queue.task_done()


class theHarvester:
    """theHarvester class"""

    def __init__(self, active, data_source, domain, search_max, save_emails, delay, url_timeout, num_threads, proxy=None):
        """Initialize theHarvester object"""

        self.active = active
        self.data_source = data_source.lower()
        self.domain = domain
        self.proxies = None
        if proxy:
            self.proxies = {
                "http": proxy,
                "https": proxy
            }

        self.search_max = search_max
        if self.search_max < 100:
            self.num_max = self.search_max
        else:
            self.num_max = 100

        self.save_emails = save_emails
        self.delay = delay
        self.url_timeout = url_timeout
        self.all_emails = []
        self.parsed_emails = []

        # Create queue and specify the number of worker threads.
        self.queue = queue.Queue()
        self.num_threads = num_threads

    def go(self):
        # Kickoff the threadpool.
        for i in range(self.num_threads):  # noqa
            thread = Worker()
            thread.daemon = True
            thread.threading_object = self
            thread.start()

        if self.data_source == "google":
            self.google_search()

        else:
            print("[-] Unknown data source type: {}".format(self.data_source))
            sys.exit(0)

        # Display emails
        self.display_emails()

        # Save emails to file
        if self.save_emails and self.all_emails:
            with open("{}_{}.txt".format(self.domain, get_timestamp()), "a") as fh:
                for email in self.parsed_emails:
                    fh.write("{}\n".format(email))
        return self.parsed_emails

    def google_search(self):

        # Search for emails not within the domain's site (-site:<domain>)
        query = "{} -site:{}".format(self.domain, self.domain)

        print("[*] (PASSIVE) Searching for emails NOT within the domain's site: {}".format(query))

        for url in googlesearch.search(
            query,
            start=0,
            stop=self.search_max,
            num=self.num_max,
            pause=self.delay,
            extra_params={"filter": "0"},
            tbs="li:1",  # Verbatim mode.  Doesn't return suggested results with other domains.
        ):
            self.queue.put(url)

        # Search for emails within the domain's site (site:<domain>).
        if self.active:
            query = "site:{}".format(self.domain)

            print("[*] (ACTIVE) Searching for emails within the domain's sites: {}".format(self.domain))
            for url in googlesearch.search(
                query,
                start=0,
                stop=self.search_max,
                num=self.num_max,
                pause=self.delay,
                extra_params={"filter": "0"},
                tbs="li:1",  # Verbatim mode.  Doesn't return suggested results with other domains.
            ):
                self.queue.put(url)

        else:
            print(
                "[*] Active search (-a) not specified, skipping searching for emails within the domain's sites (*.{})".format(
                    self.domain
                )
            )

        self.queue.join()

    def display_emails(self):
        if not self.all_emails:
            print("[-] No emails found")
        else:
            self.parsed_emails = list(sorted(set([element.lower() for element in self.all_emails])))
            print("\n[+] {} unique emails found: ".format(len(self.parsed_emails)))
            print("---------------------------")
            for email in self.parsed_emails:
                print(email)


def get_timestamp():
    """Retrieve a pre-formated datetimestamp."""

    now = time.localtime()
    timestamp = time.strftime("%Y%m%d_%H%M%S", now)
    return timestamp


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="A rewrite of the classic theHarvester.")

    data_sources = ["google"]

    parser.add_argument(
        "-a",
        dest="active",
        action="store_true",
        default=False,
        help="Conduct an active search.  This could potentially scrape target domain and sub-domains from your IP (Default: False)",
    )
    parser.add_argument(
        "-x",
        dest="proxy",
        action="store",
        default=None,
        help="Add a proxy",
    )
    parser.add_argument(
        "-b",
        dest="data_source",
        action="store",
        required=True,
        default="google",
        help="Specify data source. Default: google",
    )
    parser.add_argument("-d", dest="domain", action="store", required=True, help="Domain to search")
    parser.add_argument(
        "-l", dest="search_max", action="store", type=int, default=100, help="Maximum results to search (Default: 100)"
    )
    parser.add_argument(
        "-f",
        dest="save_emails",
        action="store_true",
        default=False,
        help="Save the emails to emails_<TIMESTAMP>.txt file",
    )
    parser.add_argument(
        "-e",
        dest="delay",
        action="store",
        type=float,
        default=7.0,
        help="""Delay (in seconds) between searches.  If it's too small Google may block your IP, too big and your search
        may take a while (Default: 7.0).""",
    )
    parser.add_argument(
        "-t",
        dest="url_timeout",
        action="store",
        type=int,
        default=60,
        help="Number of seconds to wait before timeout for unreachable/stale pages (Default: 60)",
    )
    parser.add_argument(
        "-n", dest="num_threads", action="store", type=int, default=8, help="Number of search threads (Default: 8)"
    )

    args = parser.parse_args()

    if args.data_source.lower() not in data_sources:
        print("[-] Invalid search engine...specify (" + ", ".join(data_sources) + ")")
        sys.exit(0)
    if args.delay < 0:
        print("[!] Delay (-e) must be greater than 0")
        sys.exit(0)
    if args.url_timeout < 0:
        print("[!] URL timeout (-t) must be greater than 0")
        sys.exit(0)
    if args.num_threads < 0:
        print("[!] Number of threads (-n) must be greater than 0")
        sys.exit(0)

    th = theHarvester(**vars(args))
    th.go()

    print("\n[+] Done!")
