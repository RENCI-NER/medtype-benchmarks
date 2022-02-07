#!/usr/bin/env python3

# A script for merging information from multiple PubAnnotator files.
# We can do it by multiple methods:
#   - By default, we merge entries from all files; entries having the same
#     source_url are assumed to be identical and their tracks will be merged
#     rather than being duplicated.
#   - However, you can also turn on `--annotate-first` mode, which will only
#     add tracks to the first file given.

import logging
import json
import glob
import os
import time

import click
import requests

logging.basicConfig(level=logging.INFO)

def merge_file(input_path, output_file, kwargs):
    """
    Merge an individual file into an output using the criteria provided.

    :param input_path: Input file path
    :param output_file: Output file path
    :param kwargs: configuration parameters from the command line
    """

    with open(input_path) as input:
        for line in input:
            entry = json.loads(line)



@click.command()
@click.argument('input', nargs=-1, type=click.Path(
    file_okay=True,
    dir_okay=True,
    exists=True
))
@click.option('--output', '-O', default='-', type=click.File('w'))
@click.option('--annotate-first', type=bool)
def merge(input, output, **kwargs):
    """
    merge.py [files or directories containing JSONL files to merge]
    """
    for inp in input:
        input_path = click.format_filename(inp)

        if os.path.isdir(input_path):
            # TODO: make this better.
            logging.info(f"Globbing: {f'{input_path}/**/*.jsonl'}.")
            for filename in glob.iglob(f'{input_path}/**/*.jsonl', recursive=True):
                merge_file(filename, output, kwargs)
        else:
            merge_file(input_path, output, kwargs)


if __name__ == '__main__':
    merge()
