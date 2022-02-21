#!/usr/bin/python3

#
# Filter a PubAnnotator file
#
import os

import glob
import requests
import click
import functools
import json
import logging

logging.basicConfig(level=logging.INFO)


def filter_by_pmid_list(input, output, pmid_list: set):
    with open(output, 'w') as fout:
        with open(input, 'r') as f:
            for (index, line) in enumerate(f):
                if line.strip() == '':
                    continue
                entry = json.loads(line)
                logging.debug(f"{input} line {index}: {entry}")

                # Write the entry into the output file.
                if entry['source_url'].startswith('https://pubmed.ncbi.nlm.nih.gov/'):
                    pmid = entry['source_url'][32:]
                    if pmid.endswith('/'):
                        pmid = pmid[:-1]
                else:
                    raise RuntimeError(f"Could not parse source ID: {entry['source_url']}")

                # Look for this PMID in the pmid_list
                if pmid in pmid_list:
                    logging.info(f"Found PMID {pmid}")
                    json.dump(entry, fout)
                    fout.write("\n")
                else:
                    logging.info(f"PMID {pmid} not found")


@click.command()
@click.argument('input', type=click.Path(
    file_okay=True,
    dir_okay=False,
    readable=True,
    allow_dash=False
))
@click.option('--output', '-O', default='-', type=click.Path(
    file_okay=True,
    dir_okay=False,
    writable=True,
    allow_dash=True
), help='Directory to write output files to')
@click.option('--pmid-list', type=click.File('r'))
def filter(input, output, pmid_list):

    input_path = click.format_filename(input)
    output_path = click.format_filename(output)

    # TODO: this could become a simple cat-tool as well (when run with no filters).
    if pmid_list:
        pmid_set = set()
        for line in pmid_list:
            pmid_set.add(line.strip())

        logging.debug(f"Filtering to PMIDs: {pmid_set}")

        filter_by_pmid_list(input_path, output_path, pmid_list)


if __name__ == '__main__':
    filter()
