"""
This tool aims to convert CSV into Markdown tables
"""
import argparse
import csv
import os
import sys
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.utils import fatal, LINE_FEED as LF, CARRIAGE_RETURN as CR


class CsvConverter:
    def __init__(self, input_file, output_file=None, headers=None):
        self.input_file = Path(input_file).absolute()
        self.output_file = None
        if output_file:
            self.output_file = Path(output_file).absolute()
        if not self.input_file.exists():
            raise FileNotFoundError(f"File {self.input_file} does not exist")
        if self.input_file == self.output_file:
            raise ValueError(f"Input file must be different from output file")

    def convert(self):
        with open(str(self.input_file)) as csv_file:
            reader = csv.DictReader(csv_file)
            msg = f"|{'|'.join([x.capitalize() for x in reader.fieldnames])}|{LF}"
            msg += f"|{'|'.join(['---' for i in range(len(reader.fieldnames))])}|{LF}"
            for line in reader:
                for k, v in line.items():
                    if isinstance(v, list):
                        line[k] = v[0]
                        line[k].replace("|", "-")
                    elif v.find("|") > -1:
                        line[k] = line[k].replace("|", "-")
                msg += f"|{'|'.join([e.replace(LF, CR).replace('|', '-') for e in line.values()])}|{LF}"

            if not self.output_file:
                print(msg)
            else:
                with open(self.output_file, 'a') as out:
                    out.write(LF)
                    out.write(msg)


def get_args():
    parser = argparse.ArgumentParser(description="CSV to Markdown Converter")
    parser.add_argument("-s", "--skip-fieldnames", action="store_true", required=False, default=False,
                        help="Build table without field names")
    parser.add_argument("-H", "--fieldnames", type=str, required=False, default=None,
                        help="Generate the table using the provided field names")
    parser.add_argument("-o", "--output", type=str, required=False, default=None,
                        help="Output to file")
    parser.add_argument("input_file", help="Input CSV file")
    return parser.parse_args()


def main(args):
    converter = CsvConverter(input_file=args.input_file, output_file=args.output, headers=args.fieldnames)
    converter.convert()


if __name__ == '__main__':
    if os.name == "nt":
        os.system("color")
    args = get_args()
    try:
        main(args)
    except Exception as e:
        fatal(f"{e}")
