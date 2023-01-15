#!/usr/bin/env python3
import argparse
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", help="output file")
parser.add_argument("input_files", nargs="*", help="input_files")
args = parser.parse_args()

output = Counter()
for filename in args.input_files:
    with open(filename) as ud_file:
        for line in ud_file.readlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entry = line.split("\t")
            form = entry[1]
            upos = entry[3]
            if upos in {"PUNCT", "SYM", "X"}:
                continue
            output[form] += 1

with open(args.output, "w") as output_file:
    for form, n in output.most_common():
        output_file.write(form + "\t" + str(n) + "\n")
