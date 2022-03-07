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
import re
import time

import click
import requests

logging.basicConfig(level=logging.INFO)

conf_limit = 1000


def score_file(input_path, output_file, filter):
    """ Score an individual file and write it out to the given file. """
    filter_set = set(filter)

    with open(input_path, 'r') as f:
        # Collect all the denotations that span the same area.
        denotations_by_span = {}

        for line in f:
            global conf_limit
            conf_limit -= 1
            if conf_limit < 0:
                break
            logging.debug(f"Scoring {line[:100]}")
            entry = json.loads(line)

            def add_denotation(project, denotation):
                source_url = entry['source_url']
                logging.debug(f"{source_url} add_denotation({project}, {denotation})")

                # Add the project to the denotation.
                d = dict(denotation)
                d['project'] = project

                # Extract span.
                denotation_begin = d['span']['begin']
                denotation_end = d['span']['end']

                # Look for an overlapping denotation.
                flag_key_matched = False
                for key in denotations_by_span.keys():
                    m = re.match('^(\\d+)_(\\d+)$', key)
                    if not m:
                        raise RuntimeError(f"Key {key} is incorrectly formatted")

                    span_start = int(m.group(1))
                    span_end = int(m.group(2))

                    # We currently define overlap as having at least one character overlap.
                    if int(denotation_begin) <= span_end and int(denotation_end) >= span_start:
                        denotations_by_span[key].append(d)
                        flag_key_matched = True

                if not flag_key_matched:
                    # We couldn't find a match, so let's just add this.
                    denotations_by_span[f"{denotation_begin}_{denotation_end}"] = [d]

            tracks = entry['tracks']
            if not isinstance(tracks, list):
                tracks = [tracks]
            for track in tracks:
                project = track['project']
                if len(filter) > 0 and project not in filter_set:
                    continue
                denotations = track['denotations']
                for denotation in denotations:
                    add_denotation(project, denotation)

        # Calculate scores
        print("Denotations:")
        for span in denotations_by_span.keys():
            count = len(denotations_by_span[span])
            if count > 1:
                print(f" - {span} ({count} annotations):")
                for den in denotations_by_span[span]:
                    if isinstance(den['obj'], list) and 'biolink:NamedThing' in den['obj']:
                        print(f"  - [BIOLINK] {den['text']}: {den}")
                    else:
                        print(f"  - {den['text']}: {den}")


@click.command()
@click.argument('input', type=click.Path(
    file_okay=True,
    dir_okay=True,
    exists=True
))
@click.option('--output', '-O', default='-', type=click.File('w'))
@click.option('--filter', '-f', help='List of projects whose tracks should be included (all other tracks are filtered out)', multiple=True)
def score(input, output, filter):
    """
    score.py [PubAnnotator JSONL file or directory to annotate]
    """
    input_path = click.format_filename(input)

    # logging.info(f"Globbing: {f'{input_path}/**/*.jsonl'}.")

    if os.path.isdir(input_path):
        # TODO: make this better.
        for filename in glob.iglob(f'{input_path}/**/*.jsonl', recursive=True):
            score_file(filename, output, filter)
    else:
        score_file(input_path, output, filter)


if __name__ == '__main__':
    score()
