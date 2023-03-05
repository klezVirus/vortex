import argparse
import os.path
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="File to convert")
    args = parser.parse_args()

    csv_file = os.path.splitext(args.file)[0] + ".csv"
    csv_lines = []
    with open(args.file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if re.search(r"^(\|\s*-+\s*)+\s*\|\s*$", line):
                continue
            csv_lines.append(line.replace("|", ",").replace("\n", ""))

    print("[+] Writing CSV file to {}".format(csv_file))
    with open(csv_file, "w") as f:
        for line in csv_lines:
            f.write(line + "\n")

if __name__ == '__main__':
    main()
