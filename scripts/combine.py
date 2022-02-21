#!/usr/bin/python3

#
# Combine PubAnnotator files
# Given how large these files can be, by default we'll use the following algorithm:
#   1. Identify the smaller of two input file.
#   2. Go through the entries in the larger input file. For each entry, look for a matching entry
#      in the other file. If found, combine and write out the output.
# I will eventually add options for loading the entire input file into memory.
#
import os

import glob
import requests
import click
import functools
import json
import logging

logging.basicConfig(level=logging.INFO)


def combine2(smaller_input, larger_input, output):
    with open(output, 'w') as fout:
        with open(larger_input, 'r') as f:
            for (index, line) in enumerate(f):
                if line.strip() == '':
                    continue
                entry = json.loads(line)
                logging.debug(f"{larger_input} line {index}: {entry}")

                # Write the entry into the output file.
                if entry['source_url'].startswith('https://pubmed.ncbi.nlm.nih.gov/'):
                    pmid = entry['source_url'][32:]
                    if pmid.endswith('/'):
                        pmid = pmid[:-1]
                else:
                    raise RuntimeError(f"Could not parse source ID: {entry['source_url']}")

                # Look for this PMID in the other file
                flag_found_in_smaller = False
                with open(smaller_input, 'r') as fsmall:
                    for (index_smaller, line_smaller) in enumerate(fsmall):
                        if line_smaller.strip() == '':
                            continue
                        entry_smaller = json.loads(line_smaller)
                        logging.debug(f"{smaller_input} line {line_smaller}: {entry_smaller}")

                        # Read an entry from the smaller file.
                        if entry_smaller['source_url'].startswith('https://pubmed.ncbi.nlm.nih.gov/'):
                            pmid_smaller = entry_smaller['source_url'][32:]
                            if pmid_smaller.endswith('/'):
                                pmid_smaller = pmid_smaller[:-1]
                        else:
                            raise RuntimeError(f"Could not parse source ID: {entry_smaller['source_url']}")

                        if pmid_smaller == pmid:
                            logging.info(f"Found PMID {pmid} shared between input files, combining.")
                            flag_found_in_smaller = True

                            # Add new annotations from entry_smaller to entry.
                            tracks = entry['tracks']
                            projects = set(list(map(lambda tr: tr['project'], tracks)))
                            tracker_smaller = entry_smaller['tracks']
                            for track_smaller in tracker_smaller:
                                project_smaller = track_smaller['project']
                                if project_smaller in projects:
                                    logging.info(f"Track with project {project_smaller} found, skipping")
                                else:
                                    logging.info(f"Track with project {project_smaller} not found, adding.")
                                    entry['tracks'].append(track_smaller)

                logging.info(f"Completed checks for {pmid}, found = {flag_found_in_smaller}")

                # Write to the output file.
                json.dump(entry, fout)
                fout.write("\n")

@click.command()
@click.argument('input1', type=click.Path(
    file_okay=True,
    dir_okay=True,
    readable=True,
    allow_dash=False
))
@click.argument('input2', type=click.Path(
    file_okay=True,
    dir_okay=True,
    readable=True,
    allow_dash=False
))
@click.option('--output', '-O', default='-', type=click.Path(
    file_okay=True,
    dir_okay=False,
    writable=True,
    allow_dash=True
), help='Directory to write output files to')
def combine(input1, input2, output):
    """
    Given a PubAnnotator input file and a track name, this script will create an additional track called
    'track+NodeNorm' with original track node normalized.
    """

    input1_path = click.format_filename(input1)
    input2_path = click.format_filename(input2)
    output_path = click.format_filename(output)

    # logging.info(f"Globbing: {f'{input_path}/**/*.jsonl'}.")

    smaller_input = input1_path
    larger_input = input2_path
    if os.path.getsize(smaller_input) > os.path.getsize(larger_input):
        smaller_input = input2_path
        larger_input = input1_path

    combine2(smaller_input, larger_input, output_path)


if __name__ == '__main__':
    combine()
