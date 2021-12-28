#### Introduction

One of the most popular tools to collect email addresses and other target information during a pen test is [theHarvester](http://www.edge-security.com/theharvester.php), written by Christian Martorella [@laramies](http://twitter.com/laramies) of the [Edge-Security Group](http://www.edge-security.com/).  The source code can be found here: [https://github.com/laramies/theHarvester](https://github.com/laramies/theHarvester), but it comes with Kali by default.  Motivated by the rewrite of [metagoofil](https://github.com/opsdisk/metagoofil), I decided to rewrite theHarvester, and update the email collection portion. Currently,the DNS portion is not included.


#### Installation

Clone the git repository and install the requirements.

```bash
pip3 install -r requirements.txt
```

#### theHarvester Collection Modes

The new theHarvester offers both the traditional passive and a new active email collection mode.


##### Passive Mode

In passive mode, the updated theHarvester searches Google for pages utilizing the `example.com -site:example.com` search criteria.  This allows the script to passively find emails on sites, like forums, that are not necessarily affiliated with the target domain, because of the `-` search operator in front of `site` [https://support.google.com/websearch/answer/2466433](https://support.google.com/websearch/answer/2466433).


##### Active Mode

The active mode searches Google for pages utilizing the `site:example.com` search criteria.  The Python `google` package is used to handle all the logic and heavy lifting of accurately searching Google for URLs.  I cover more about the the `google` package in the [metagoofil](http://blog.opsdisk.com/metagoofil/) blog post.

Once a list of URLs from the Google search results is retrieved, the script visits each site, and scrapes the page looking for email addresses.  This is considered active reconnaissance since each site is being visited from one IP and the behavior looks like a bot.


#### Switch Updates

The remaining updates deal with the switches.  The same switches were kept as in the original metagoofil to avoid confusion, with new ones also added.

The `-a` switch specifies active mode, and specifies to scrape and search for emails on the target domain and possible sub-domains.  This could be considered noisy and a precursor to a social engineering attack.

The `-f` switch writes all the emails to a `domain + date-time stamped` .txt file (e.g., example.com\_20151201_175822) instead of an HTML file.  This allows for quick copy/paste or as an input file for other tools.

The addition of the `-e` delay switch allows you to specify the time delay in seconds between searches.  If you request searches too quickly, Google will think you are a script or bot and will block your IP address for a while.  Experiment to see what works best for you.

The `-n` switch specifies the amount of threads to use during active URL retrieval to search for email addresses, with the default being 8.

Lastly, the `-t` switch specifies the amount of time to wait before trying to access a stale/defunct site in active search mode.


#### Extracting Emails

The original theHarvester had a module to clean up HTML results in order to extract emails.  The email cleaning portion of that module is folded into the `googlesearch` module code.  The email regular expression is still the same.


#### Data Presentation

The emails are converted to lowercase and sorted in alphabetical order for a cleaner look.


#### Final Thoughts

The current theHarvester passive approach is stealthier, because it only extracts email addresses from the Google search results, however, the active mode is more comprehensive.  The stealth vs quantity decision is up to you as a pen tester.


#### Future Work

Not sure if I will add the other search engine functionality (Yahoo!, Baidu), the API key depednent seraching (Shodan), or the other tools (dnsenum, dnsrecon).  Usually during a social engineering campaign, I really only care about the email addresses.


#### Conclusion

All of the code can be found on the Opsdisk Github repository here: https://github.com/opsdisk/theHarvester.  Comments, suggestions, and improvements are always welcome.  Be sure to follow [@opsdisk](https://twitter.com/opsdisk) on Twitter for the latest updates.
