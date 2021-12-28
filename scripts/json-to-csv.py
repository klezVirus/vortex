import json
import os

import pandas as pd
import argparse


def detect_columns(json_file):
    with open(json_file) as json_in:
        dictionary = json.load(json_in)
        if isinstance(dictionary, dict):
            return dictionary.keys()
        elif isinstance(dictionary, list):
            return dictionary[0].keys()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="JSON to CSV using Pandas")
    parser.add_argument("json", help="The JSON file to convert")
    parser.add_argument("csv", help="The CSV output file")
    parser.add_argument("-t", "--type", choices=["profil3r", "sn0int"], default="sn0int",
                        help="The type of JSON file to convert")
    parser.add_argument("-l", "--linearize", action="store_true", default=False,
                        help="The CSV output file will be linearised")
    args = parser.parse_args()

    if not os.path.isfile(args.json):
        raise FileNotFoundError

    choice = "n"
    if os.path.isfile(args.csv):
        print(f"[-] File {args.csv} exists. Overwrite?")
        choice = input("[y|n] $> ")
        if choice.lower() != "y":
            exit(1)

    columns = detect_columns(args.json)

    if args.type == "sn0int":
        df = pd.read_json(args.json)

        new_df = df
        if args.linearize:
            new_df = df.merge(df.credentials.apply(pd.Series), left_on="uid", right_index=True)
            new_df = new_df.drop(columns=["credentials"])
            new_df.index.names = ["uid"]

        new_df.to_csv(args.csv, index=None)

    elif args.type == "profil3r":
        new_dictionary = {}
        with open(args.json) as json_in:
            dictionary = json.load(json_in)
        for c in columns:
            new_dictionary[c] = [dictionary[c]["accounts"][i]["value"] for i in range(len(dictionary[c]["accounts"]))]

        print(new_dictionary)

