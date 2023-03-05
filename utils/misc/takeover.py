from time import time

from dns.name import EmptyLabel
from tqdm import tqdm
from gc import collect
from re import findall
from sys import stderr
from requests import get
from warnings import simplefilter
from dns.exception import DNSException
from configparser import RawConfigParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dns.resolver import Resolver, NXDOMAIN, NoAnswer, NoNameservers, Timeout

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
           "Content-Type": "application/json"}
signatures = {
    "Amazon AWS/S3": ["NoSuchBucket"],
    "Bitbucket": ["Repository not found"],
    "Campaign Monitor": ["Double check the URL or <a href=\"mailto:help@createsend.com"],
    "Cargo Collective": ["<title>404 &mdash; File not found</title>"],
    "Feedpress": ["The feed has not been found."],
    "Ghost.io": ["The thing you were looking for is no longer here, or never was"],
    "Github": ["There isn't a GitHub Pages site here."],
    "Helpjuice": ["There's nothing here, yet.", "We could not find what you're looking for."],
    "Helpscout": ["No settings were found for this company"],
    "Heroku": ["<title>No such app</title>"],
    "JetBrains": ["is not a registered InCloud YouTrack"],
    "Readme.io": ["Project doesnt exist... yet!"],
    "Surge.sh": ["project not found"],
    "Tumblr": ["Whatever you were looking for doesn't currently exist at this address."],
    "Tilda": ["Domain has been assigned."],
    "Tilda 2": ["Please renew your subscription"],
    "UserVoice": ["Perhaps you meant to visit", "This UserVoice subdomain is currently available!"],
    "Wordpress": ["Do you want to register"],
    "Strikingly": ["But if you're looking to build your own website"],
    "Uptime Robot": ["page not found"],
    "Pantheon": ["The gods are wise"],
    "Teamwork": ["Oops - We didn't find your site."],
    "Intercom": ["This page is reserved for artistic dogs"],
    "Webflow": ["The page you are looking for doesn't exist or has been moved"],
    "Wishpond": ["https://www.wishpond.com/404?campaign=true"],
    "Aftership": ["Oops.</h2><p class=\"text-muted text-tight\">The page you're looking for doesn't exist."],
    "Aha!": ["There is no portal here ... sending you back to Aha!"],
    "Brightcove": ["<p class=\"bc-gallery-error-code\">Error Code: 404</p>"],
    "Bigcartel": ["<h1>Oops! We couldn&#8217;t find that page.</h1>"],
    "Acquia": ["Sorry, we could not find any content for this web address"],
    "Simplebooklet": [">Sorry, we can't find this <a"],
    "Getresponse": ["With GetResponse Landing Pages, lead generation has never been easier"],
    "Vend": ["Looks like you've traveled too far into cyberspace"],
    "Tictail": ["to target URL: <a href=\"https://tictail.com"],
    "Fly.io": ["not found:"],
    "Desk": ["Sorry, we couldn't find that page."],
    "Zendesk": ["Help Center Closed"],
    "Statuspage": ["Statuspage | Hosted Status Pages for Your Company"],
    "Thinkific": ["You may have mistyped the address or the page may have moved."],
    "Tave": ["You're at a page that doesn't exist."],
    "Activecampaign": ["LIGHTTPD - fly light."],
    "Pingdom": ["Sorry, couldn&rsquo;t find the status page"],
    "Surveygizmo": ["609-6480"],
    "Mashery": ["Unrecognized domain <strong>"],
    "Instapage": ["Looks Like You're Lost"],
    "Kajabi": ["No such app", "not found"],
    "Airee": ["https://xn--80aqc2a.xn--p1ai/"],
    "Hatena": ["404 Blog is not found"],
    "Launchrock": ["you may have taken a wrong turn somewhere"],
    "Kayako": ["That's not an active Kayako account"],
    "Ning": ["Please double-check the address you've just entered", "is free to take"],
    "Moosend": ["One account fits everything:"]

}


def findSignatures(domainToTry, signatures, neededMatches):
    numberOfMatches = 0

    try:
        for signature in signatures:
            if signature in str(get("http://" + domainToTry, headers=headers, verify=False).content, "utf-8"):
                numberOfMatches += 1

                if neededMatches <= numberOfMatches:
                    return True

    except Exception:
        pass

    try:
        for signature in signatures:
            if signature in str(get("https://" + domainToTry, headers=headers, verify=False).content, "utf-8"):
                numberOfMatches += 1

                if neededMatches <= numberOfMatches:
                    return True

    except Exception:
        pass

    return False


def findNX(domainToTry):
    resolver = Resolver()
    resolver.timeout = 1
    resolver.lifetime = 1

    try:
        resolver.query(domainToTry)

    except NXDOMAIN:
        return True

    except Exception:
        pass

    return False


def amazonS3(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Amazon AWS/S3"], 2):
        outcome = ["Amazon AWS/S3", domain, CNAME]

    return outcome


def bitbucket(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(CNAME, signatures["Bitbucket"], 1):
        outcome = ["Bitbucket", domain, CNAME]

    return outcome


def campaignMonitor(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(CNAME, signatures["Campaign Monitor"], 1):
        outcome = ["Campaign Monitor", domain, CNAME]

    return outcome


def desk(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Desk"], 1):
        outcome = ["Desk", domain, CNAME]

    return outcome


def zendesk(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Zendesk"], 1):
        outcome = ["Zendesk", domain, CNAME]

    return outcome


def statuspage(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Statuspage"], 1):
        outcome = ["Statuspage", domain, CNAME]

    return outcome


def thinkific(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Thinkific"], 1):
        outcome = ["Thinkific", domain, CNAME]

    return outcome


def tave(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Tave"], 1):
        outcome = ["Tave", domain, CNAME]

    return outcome


def activecampaign(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Activecampaign"], 1):
        outcome = ["Activecampaign", domain, CNAME]

    return outcome


def pingdom(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Pingdom"], 1):
        outcome = ["Pingdom", domain, CNAME]

    return outcome


def surveygizmo(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Surveygizmo"], 2):
        outcome = ["Surveygizmo", domain, CNAME]

    return outcome


def mashery(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Mashery"], 1):
        outcome = ["Mashery", domain, CNAME]

    return outcome


def instapage(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Instapage"], 1):
        outcome = ["Instapage", domain, CNAME]

    return outcome


def kajabi(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Kajabi"], 2):
        outcome = ["Kajabi", domain, CNAME]

    return outcome


def airee(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Airee"], 1):
        outcome = ["Airee", domain, CNAME]

    return outcome


def hatena(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Hatena"], 2):
        outcome = ["Hatena", domain, CNAME]

    return outcome


def launchrock(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Launchrock"], 1):
        outcome = ["Launchrock", domain, CNAME]

    return outcome


def flyio(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(CNAME, signatures["Fly.io"], 1):
        outcome = ["Fly.io", domain, CNAME]

    return outcome


def cargoCollective(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(CNAME, signatures["Cargo Collective"], 1):
        outcome = ["Cargo Collective", domain, CNAME]

    return outcome


def cloudfront(domain, ARecords, CNAME):
    outcome = []
    # implement me - odd case
    return outcome


def fastly(domain, ARecords, CNAME):
    outcome = []
    # implement me - odd case
    return outcome


def feedpress(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Feedpress"], 2):
        outcome = ["Feedpress", domain, CNAME]

    return outcome


def ghost(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Ghost.io"], 1):
        outcome = ["Ghost.io", domain, CNAME]

    return outcome


def github(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Github"], 1):
        outcome = ["Github", domain, CNAME]

    return outcome


def helpjuice(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(CNAME, signatures["Helpjuice"], 1):
        outcome = ["Helpjuice", domain, CNAME]

    return outcome


def helpscout(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Helpscout"], 1):
        outcome = ["Helpscout", domain, CNAME]

    return outcome


def heroku(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(CNAME, signatures["Heroku"], 2):
        outcome = ["Heroku", domain, CNAME]

    return outcome


def jetbrains(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["JetBrains"], 1):
        outcome = ["JetBrains", domain, CNAME]

    return outcome


def azure(domain, ARecords, CNAME):
    outcome = []

    if findNX(CNAME):
        outcome = ["Azure", domain, CNAME]

    return outcome


def netlify(domain, ARecords, CNAME):
    outcome = []
    # implement me - odd case
    return outcome


def readme(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Readme.io"], 1):
        outcome = ["Readme.io", domain, CNAME]

    return outcome


def shopify(domain, ARecords, CNAME):
    outcome = []
    # implement me - odd case
    return outcome


def surge(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Surge.sh"], 1):
        outcome = ["Surge.sh", domain, CNAME]

    return outcome


def tumblr(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Tumblr"], 1):
        outcome = ["Tumblr", domain, CNAME]

    return outcome


def tilda(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Tilda"], 1) or findSignatures(domain, signatures["Tilda 2"], 1):
        outcome = ["Tilda", domain, CNAME]

    return outcome


def uservoice(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["UserVoice"], 1):
        outcome = ["UserVoice", domain, CNAME]

    return outcome


def wordpress(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Wordpress"], 1):
        outcome = ["Wordpress", domain, CNAME]

    return outcome


def smugmug(domain, ARecords, CNAME):
    outcome = []

    try:
        if get("http://" + domain, headers=headers).status_code == 404:
            outcome = ["Smugmug", domain, CNAME]
            return outcome

    except Exception:
        pass

    try:
        if get("https://" + domain, headers=headers, verify=False).status_code == 404:
            outcome = ["Smugmug", domain, CNAME]
            return outcome

    except Exception:
        pass

    resolver = Resolver()
    resolver.timeout = 1
    resolver.lifetime = 1

    try:
        resolver.query(CNAME)

    except NXDOMAIN:
        outcome = ["Smugmug", domain, CNAME]

    return outcome


def strikingly(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Strikingly"], 1):
        outcome = ["Strikingly", domain, CNAME]

    return outcome


def uptimerobot(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Uptime Robot"], 1):
        outcome = ["Uptime Robot", domain, CNAME]

    return outcome


def pantheon(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Pantheon"], 1):
        outcome = ["Pantheon", domain, CNAME]

    return outcome


def teamwork(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Teamwork"], 1):
        outcome = ["Teamwork", domain, CNAME]

    return outcome


def intercom(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Intercom"], 1):
        outcome = ["Intercom", domain, CNAME]

    return outcome


def webflow(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Webflow"], 1):
        outcome = ["Webflow", domain, CNAME]

    return outcome


def wishpond(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Wishpond"], 1):
        outcome = ["Wishpond", domain, CNAME]

    return outcome


def aftership(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Aftership"], 1):
        outcome = ["Aftership", domain, CNAME]

    return outcome


def aha(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Aha!"], 1):
        outcome = ["Aha!", domain, CNAME]

    return outcome


def tictail(domain, ARecords, CNAME):
    outcome = []

    try:
        if signatures["Tictail"] in str(get("http://" + domain, headers=headers).history[0].content, "utf-8"):
            outcome = ["Tictail", domain, CNAME]
            return outcome

        if signatures["Tictail"] in str(get("https://" + domain, headers=headers, verify=False).history[0].content,
                                        "utf-8"):
            outcome = ["Tictail", domain, CNAME]
            return outcome

    except Exception:
        pass

    return outcome


def brightcove(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Brightcove"], 1):
        outcome = ["Brightcove", domain, CNAME]

    return outcome


def bigcartel(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Bigcartel"], 1):
        outcome = ["Bigcartel", domain, CNAME]

    return outcome


def acquia(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Acquia"], 1):
        outcome = ["Acquia", domain, CNAME]

    return outcome


def simplebooklet(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Simplebooklet"], 1):
        outcome = ["Simplebooklet", domain, CNAME]

    return outcome


def getresponse(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Getresponse"], 1):
        outcome = ["Getresponse", domain, CNAME]

    return outcome


def vend(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Vend"], 1):
        outcome = ["Vend", domain, CNAME]

    return outcome


def maxcdn(domain, ARecords, CNAME):
    outcome = []

    if findNX(CNAME):
        outcome = ["Maxcdn", domain, CNAME]

    return outcome


def apigee(domain, ARecords, CNAME):
    outcome = []

    if findNX(CNAME):
        outcome = ["Apigee", domain, CNAME]

    return outcome


def kayako(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Kayako"], 1):
        outcome = ["Kayako", domain, CNAME]

    return outcome


def ning(domain, ARecords, CNAME):
    outcome = []

    if findSignatures(domain, signatures["Ning"], 1) and findSignatures(CNAME, signatures["Ning"], 1):
        outcome = ["Ning", domain, CNAME]

    return outcome


def moosend(domain, ARecords, CNAME):
    outcome = []

    if "m-pages.com" in CNAME:
        outcome = ["Moosend Landing Page", domain, CNAME]

    elif not findSignatures(domain, signatures["Moosend"], 1):
        outcome = ["Moosend", domain, CNAME]

    return outcome


def identify(domain, ARecords, CNAMERecords):
    outcome = []

    for entry in CNAMERecords:
        CNAME = str(entry)[:-1]

        if findall(".*s3.*.amazonaws\.com", CNAME):
            outcome = amazonS3(domain, ARecords, CNAME)

        elif "bitbucket.io" in CNAME:
            outcome = bitbucket(domain, ARecords, CNAME)

        elif ".desk.com" in CNAME:
            outcome = desk(domain, ARecords, CNAME)

        elif ".zendesk.com" in CNAME:
            outcome = zendesk(domain, ARecords, CNAME)

        elif "statuspage.io" in CNAME:
            outcome = statuspage(domain, ARecords, CNAME)

        elif "thinkific.com" in CNAME:
            outcome = thinkific(domain, ARecords, CNAME)

        elif "clientaccess.tave.com" in CNAME:
            outcome = tave(domain, ARecords, CNAME)

        elif "activehosted.com" in CNAME:
            outcome = activecampaign(domain, ARecords, CNAME)

        elif "stats.pingdom.com" in CNAME:
            outcome = pingdom(domain, ARecords, CNAME)

        elif "privatedomain.sgizmo.com" in CNAME or "privatedomain.surveygizmo.eu" in CNAME or "privatedomain.sgizmoca.com" in CNAME:
            outcome = surveygizmo(domain, ARecords, CNAME)

        elif "mashery.com" in CNAME:
            outcome = mashery(domain, ARecords, CNAME)

        elif "pageserve.co" in CNAME or "secure.pageserve.co" in CNAME:
            outcome = instapage(domain, ARecords, CNAME)

        elif "endpoint.mykajabi.com" in CNAME or "ssl.kajabi.com" in CNAME:
            outcome = kajabi(domain, ARecords, CNAME)

        elif "cdn.airee.ru" in CNAME:
            outcome = airee(domain, ARecords, CNAME)

        elif "hatenablog.com" in CNAME or "hatenadiary.com" in CNAME:
            outcome = hatena(domain, ARecords, CNAME)

        elif "launchrock.com" in CNAME:
            outcome = launchrock(domain, ARecords, CNAME)

        elif "edgeapp.net" in CNAME:
            outcome = flyio(domain, ARecords, CNAME)

        elif "createsend.com" in CNAME:
            outcome = campaignMonitor(domain, ARecords, CNAME)

        elif "cargocollective.com" in CNAME:
            outcome = cargoCollective(domain, ARecords, CNAME)

        elif "kayako.com" in CNAME:
            outcome = kayako(domain, ARecords, CNAME)

        elif "ning.com" in CNAME:
            for entry in ARecords:
                if str(entry) == "208.82.16.68":
                    outcome = ning(domain, ARecords, CNAME)

        elif "moosend.com" in CNAME or "m-pages.com" in CNAME:
            outcome = moosend(domain, ARecords, CNAME)

        elif "herokuapp.com" in CNAME:
            outcome = heroku(domain, ARecords, CNAME)

        elif "redirect.feedpress.me" in CNAME:
            outcome = feedpress(domain, ARecords, CNAME)

        elif "ghost.io" in CNAME:
            outcome = ghost(domain, ARecords, CNAME)

        elif "github.io" in CNAME:
            outcome = github(domain, ARecords, CNAME)

        elif "helpjuice.com" in CNAME:
            outcome = helpjuice(domain, ARecords, CNAME)

        elif "helpscoutdocs.com" in CNAME:
            outcome = helpscout(domain, ARecords, CNAME)

        elif "myjetbrains.com" in CNAME:
            outcome = jetbrains(domain, ARecords, CNAME)

        elif "readme.io" in CNAME or "ssl.readmessl.com" in CNAME:
            outcome = readme(domain, ARecords, CNAME)

        elif "surge.sh" in CNAME:
            outcome = surge(domain, ARecords, CNAME)

        elif "domains.tumblr.com" in CNAME:
            outcome = tumblr(domain, ARecords, CNAME)

        elif "uservoice.com" in CNAME:
            outcome = uservoice(domain, ARecords, CNAME)

        elif "domains.smugmug.com" in CNAME:
            outcome = smugmug(domain, ARecords, CNAME)

        elif "s.strikinglydns.com" in CNAME:
            outcome = strikingly(domain, ARecords, CNAME)

        elif "stats.uptimerobot.com" in CNAME:
            outcome = uptimerobot(domain, ARecords, CNAME)

        elif "pantheonsite.io" in CNAME:
            outcome = pantheon(domain, ARecords, CNAME)

        elif "teamwork.com" in CNAME:
            outcome = teamwork(domain, ARecords, CNAME)

        elif "custom.intercom.help" in CNAME:
            outcome = intercom(domain, ARecords, CNAME)

        elif "wishpond.com" in CNAME:
            outcome = wishpond(domain, ARecords, CNAME)

        elif "aftership.com" in CNAME:
            outcome = aftership(domain, ARecords, CNAME)

        elif "ideas.aha.io" in CNAME:
            outcome = aha(domain, ARecords, CNAME)

        elif "domains.tictail.com" in CNAME:
            outcome = tictail(domain, ARecords, CNAME)

        elif "bigcartel.com" in CNAME:
            outcome = bigcartel(domain, ARecords, CNAME)

        elif "simplebooklet.com" in CNAME:
            outcome = simplebooklet(domain, ARecords, CNAME)

        elif ".gr8.com" in CNAME:
            outcome = getresponse(domain, ARecords, CNAME)

        elif "vendecommerce.com" in CNAME:
            outcome = vend(domain, ARecords, CNAME)

        elif "netdna-cdn.com" in CNAME:
            outcome = maxcdn(domain, ARecords, CNAME)

        elif "-portal.apigee.net" in CNAME:
            outcome = apigee(domain, ARecords, CNAME)

        elif "acquia-test.co" in CNAME or "acquia-sites.com" in CNAME:
            outcome = acquia(domain, ARecords, CNAME)

        elif "bcvp0rtal.com" in CNAME or "brightcovegallery.com" in CNAME or "gallery.video" in CNAME or "cloudfront.net" in CNAME:
            outcome = brightcove(domain, ARecords, CNAME)

        elif "proxy.webflow.com" in CNAME or "proxy-ssl.webflow.com" in CNAME:
            outcome = webflow(domain, ARecords, CNAME)

        elif "wordpress.com" in CNAME:
            outcome = wordpress(domain, ARecords, CNAME)

        elif any(azureSub in CNAME for azureSub in [
            "azure-api.net", "azurecontainer.io", "azurecr.io", "azuredatalakeanalytics.net", "azuredatalakestore.net",
            "azureedge.net",
            "azurehdinsight.net", "azurefd.net", "azurehealthcareapis.com", "azureiotcentral.com", "azurewebsites.net",
            "batch.azure.com",
            "blob.core.windows.net", "cloudapp.azure.com", "cloudapp.net", "core.windows.net", "database.windows.net",
            "p.azurewebsites.net",
            "redis.cache.windows.net", "search.windows.net", "service.signalr.net", "servicebus.windows.net",
            "trafficmanager.net",
            "visualstudio.com"]):
            outcome = azure(domain, ARecords, CNAME)

    for entry in ARecords:
        if str(entry) == "66.6.44.4":
            outcome = tumblr(domain, ARecords, str(entry))

        elif str(entry) == "185.203.72.17":
            outcome = tilda(domain, ARecords, str(entry))

        elif str(entry) == "46.137.181.142":
            outcome = tictail(domain, ARecords, str(entry))

        elif str(entry) == "54.183.102.22":
            outcome = strikingly(domain, ARecords, str(entry))

        elif str(entry) == "34.193.69.252" or str(entry) == "34.193.204.92" or str(entry) == "23.235.33.229" or str(
                entry) == "104.156.81.229":
            outcome = webflow(domain, ARecords, str(entry))

        elif str(entry) == "54.243.190.28" or str(entry) == "54.243.190.39" or str(entry) == "54.243.190.47" or str(
                entry) == "54.243.190.54":
            outcome = launchrock(domain, ARecords, str(entry))

        elif "23.185.0." in str(entry) or "23.253." in str(entry):
            outcome = pantheon(domain, ARecords, str(entry))

        elif str(entry) == "192.30.252.153" or str(entry) == "192.30.252.154":
            outcome = github(domain, ARecords, str(entry))

    return outcome


def can_be_taken_over(domain, dns: dict):
    a_records = dns.get('A', [])
    cname_records = dns.get('CNAME', [])
    if a_records is None:
        a_records = []
    if cname_records is None:
        cname_records = []
    results = identify(domain, a_records, cname_records)
    return results


