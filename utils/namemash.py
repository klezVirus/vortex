#!/usr/bin/env python
import sys
import os.path


class NameMasher:
    def __init__(self, fmt=None):
        self.fmt = fmt

    def select_format(self):
        first = "first"
        last = "last"
        choice = -1
        combinations = [
            "{0}{1}",
            "{1}{0}",
            "{0}.{1}",
            "{1}.{0}",
            "{1}.{0:.1}",
            "{0:.1}{1}",
            "{1:.1}{0}",
            "{0:.1}.{1}",
            "{1:.1}.{0}",
            "{0}",
            "{1}"
        ]
        print("[+] Select a format for usernames")
        for i, c in enumerate(combinations, start=0):
            print(f"  {i}: " + c.format(first, last))

        while not 0 <= choice <= len(combinations) - 1:
            try:
                choice = int(input("  $> "))
            except KeyboardInterrupt:
                exit(1)
            except ValueError:
                continue
        self.fmt = combinations[choice]

    def mash(self, first_name, last_name):
        first_name = ''.join([c for c in first_name if c == " " or c.isalpha()])
        last_name = ''.join([c for c in last_name if c == " " or c.isalpha()])
        if not self.fmt:
            self.select_format()
        return self.fmt.format(first_name, last_name)

    def mash_list(self, name_list: list) -> list:
        ret = []
        if not self.fmt:
            self.select_format()
        for _line in name_list:
            name = ''.join([c for c in _line if c == " " or c.isalpha()])
            tokens = name.lower().split()

            # skip empty lines
            if len(tokens) < 1:
                continue

            first_name = tokens[0].strip()
            last_name = tokens[-1].strip()

            if first_name == "linkedin":
                continue

            ret.append(self.fmt.format(first_name, last_name))
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
