#!/usr/bin/env python
import re
import sys
import os.path

from nameparser import HumanName


class NameMasher:
    def __init__(self, fmt=None):
        self.fmt = fmt

    @staticmethod
    def clean_name(name2clean):
        """
        Taken directly from https://github.com/initstring/linkedin2username/blob/master/linkedin2username.py
        Why? Cause it works and I like it. Thanks, initstring!

        Removes common punctuation.
        LinkedIn's users tend to add credentials to their names to look special.
        This function is based on what I have seen in large searches, and attempts
        to remove them.
        """
        # Lower-case everything to make it easier to de-duplicate.
        name2clean = name2clean.lower()

        # Use case for tool is mostly standard English, try to standardize common non-English
        # characters.
        name2clean = re.sub(r"[àáâãäå]", 'a', name2clean)
        name2clean = re.sub(r"[èéêë]", 'e', name2clean)
        name2clean = re.sub(r"[ìíîï]", 'i', name2clean)
        name2clean = re.sub(r"[òóôõö]", 'o', name2clean)
        name2clean = re.sub(r"[ùúûü]", 'u', name2clean)
        name2clean = re.sub(r"[ýÿ]", 'y', name2clean)
        name2clean = re.sub(r"[ß]", 'ss', name2clean)
        name2clean = re.sub(r"[ñ]", 'n', name2clean)

        # Get rid of all things in parenthesis. Lots of people put various credentials, etc
        name2clean = re.sub(r'\([^()]*\)', '', name2clean)

        # The lines below basically trash anything weird left over.
        # A lot of users have funny things in their names, like () or ''
        # People like to feel special, I guess.
        allowed_chars = re.compile('[^a-zA-Z -]')
        name2clean = allowed_chars.sub('', name2clean)

        # Next, we get rid of common titles. Thanks ChatGPT for the help.
        titles = ['mr', 'miss', 'mrs', 'phd', 'prof', 'professor', 'md', 'dr', 'mba']
        pattern = "\\b(" + "|".join(titles) + ")\\b"
        name2clean = re.sub(pattern, '', name2clean)

        # The line below tries to consolidate white space between words
        # and get rid of leading/trailing spaces.
        name2clean = re.sub(r'\s+', ' ', name2clean).strip()

        return name2clean

    def select_format(self):
        first = "first"
        last = "last"
        second = "second"
        choice = -1
        combinations = [
            "{0}[{1}]{2}",
            "{0}{2}",
            "{2}{0}[{1}]",
            "{2}{0}",
            "{0}[.{1}].{2}",
            "{0}.{2}",
            "{2}.{0}[.{1}]",
            "{2}.{0}",
            "{2}.{0:.1}",
            "{2}.{0:.1}[.{1:.1}]",
            "{0:.1}{2}",
            "{0:.1}[{1:.1}]{2}",
            "{2:.1}{0}",
            "{2:.1}{0}[{1}]",
            "{0:.1}.{2}",
            "{0:.1}.[{1:.1}].{2}",
            "{2:.1}.{0}",
            "{2:.1}.{0}.[{1}]",
            "{2:.1}.{0}[{1}]",
            "{0}",
            "{1}"
            "{1}[{2}]"
        ]
        print("Select a format for usernames")
        print("  - 0: first name; 1: second name [optional]; 2: last name")
        for i, c in enumerate(combinations, start=0):
            print(f"  {i}: " + c.format(first, second, last))

        while not 0 <= choice <= len(combinations) - 1:
            try:
                choice = int(input("  $> "))
            except KeyboardInterrupt:
                exit(1)
            except ValueError:
                continue
        self.fmt = combinations[choice].replace("[", "").replace("]", "")
        return self.fmt

    def handle_name(self, full_name):
        _name = NameMasher.clean_name(full_name)
        _name = ''.join([c for c in _name if c == " " or c.isalpha()])
        _tokens = _name.lower().split()

        # skip empty lines
        if len(_tokens) < 1:
            return None

        first_name = _tokens[0].strip()
        last_name = _tokens[-1].strip()
        second_name = None
        if len(_tokens) > 2:
            second_name = "".join(_tokens[1:-1])

        if first_name == "linkedin":
            return None
        return self.mash(first_name, last_name, second_name=second_name)

    def handle_with_human_name_parser(self, noise):
        if noise.find("linkedin") != -1:
            return None
        _name = NameMasher.clean_name(noise)
        _name = ''.join([c for c in _name if c == " " or c.isalpha()])
        _name = HumanName(_name)
        return self.mash(_name.first, _name.last, second_name=_name.middle)

    def mash(self, first_name, last_name, second_name=None):
        first_name = ''.join([c for c in first_name if c == " " or c.isalpha()])
        last_name = ''.join([c for c in last_name if c == " " or c.isalpha()])
        if second_name:
            second_name = ''.join([c for c in second_name if c == " " or c.isalpha()])
        else:
            second_name = ""
        if not self.fmt:
            self.select_format()
        result = self.fmt.format(first_name, second_name, last_name)
        # Fix double dots
        result = result.replace("..", ".")
        return result

    def mash_list(self, name_list: list) -> list:
        ret = []
        if not self.fmt:
            self.select_format()
        for _line in name_list:
            _name = self.handle_name(_line)
            if _name:
                ret.append(_name)
        return ret


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: {} names.txt".format((sys.argv[0])))
        sys.exit(0)

    if not os.path.exists(sys.argv[1]):
        print("{} not found".format(sys.argv[1]))
        sys.exit(0)

    masher = NameMasher()
    for line in open(sys.argv[1]):
        name = ''.join([c for c in line if c == " " or c.isalpha()])

        tokens = name.lower().split()

        # skip empty lines
        if len(tokens) < 1:
            continue

        first = tokens[0].strip()
        last = tokens[-1].strip()

        if first == "linkedin":
            continue

        print(masher.mash(first, last))
