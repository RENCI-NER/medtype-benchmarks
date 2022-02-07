#!/usr/bin/env python3

# A script for "scoring" PubAnnotator runs. We check for three things:
#   - If spans roughly overlap (within a size parameter), we assume that they refer to the same span.
#     We combine terms and categories (separately) for each span.
#   - If a particular dataset is assumed to be definitive, we can score against that -- how many spans did each
#     track ignore, how many were identified incorrectly, identified correctly and so on.
#   - If no dataset is assumed to be definitive, we summarize how many spans each one identified, and what
#     proportion of identifications agree with other tracks.
#   - TODO: how to handle multiple concepts?

import logging
import json
import glob
import os
import time

import click
import requests

logging.basicConfig(level=logging.INFO)

def score_file(input_path, output_file):
    """ Score an individual file and write it out to the given file. """
    with open(input_path, 'r') as f:
        for line in f:

            logging.info(f"Scoring {line[:100]}")
            entry = json.loads(line)

            tracks = entry['tracks']
            for track in tracks:
                logging.info(f"{entry['source_url']}\t{track['project']}\t{len(track['denotations'])}")

@click.command()
@click.argument('input', type=click.Path(
    file_okay=True,
    dir_okay=True,
    exists=True
))
@click.option('--output', '-O', default='-', type=click.File('w'))
def score(input, output):
    """
    score.py [PubAnnotator JSONL file or directory to annotate]
    """
    input_path = click.format_filename(input)

    # logging.info(f"Globbing: {f'{input_path}/**/*.jsonl'}.")

    if os.path.isdir(input_path):
        # TODO: make this better.
        for filename in glob.iglob(f'{input_path}/**/*.jsonl', recursive=True):
            score_file(filename, output)
    else:
        score_file(input_path, output)


if __name__ == '__main__':
    score()
