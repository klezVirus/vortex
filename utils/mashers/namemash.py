#!/usr/bin/env python
import sys
import os.path

from utils.utils import info


class NameMasher:
    def __init__(self, fmt=None):
        self.fmt = fmt

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
        info("Select a format for usernames")
        info("  - 0: first name; 1: second name [optional]; 2: last name")
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
        name = ''.join([c for c in full_name if c == " " or c.isalpha()])
        tokens = name.lower().split()

        # skip empty lines
        if len(tokens) < 1:
            return None

        first_name = tokens[0].strip()
        last_name = tokens[-1].strip()
        second_name = None
        if len(tokens) > 2:
            second_name = "".join(tokens[1:-1])

        if first_name == "linkedin":
            return None
        return self.mash(first_name, last_name, second_name=second_name)

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
            name = self.handle_name(_line)
            if name:
                ret.append(name)
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
