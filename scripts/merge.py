#!/usr/bin/env python3

# A script for merging information from multiple PubAnnotator files.
# We can do it by multiple methods:
#   - By default, we merge entries from all files; entries having the same
#     source_url are assumed to be identical and their tracks will be merged
#     rather than being duplicated.
#   - However, you can also turn on `--filter-to-first` mode, which will only
#     add tracks to the first file given.

import logging
import json
import glob
import os
import time

import click
import requests

logging.basicConfig(level=logging.INFO)

def merge_file(input_path, output_path):
    """
    Merge an individual file into an output using the criteria provided.

    :param input_path: Input file path
    :param output_file: Output file path
    """

    with open(input_path) as input:
        for line in input:
            entry = json.loads(line)

            # Figure out the PMID
            source_url = entry['source_url']
            if not source_url.startswith('https://pubmed.ncbi.nlm.nih.gov/'):
                raise RuntimeError(f"Sorry, only PubMed abstracts currently supported; source URL '{source_url}' cannot be parsed.")

            pmid = source_url[32:]
            if pmid.endswith('/'):
                pmid = pmid[:-1]

            logging.info(f"Loaded entry with PMID {pmid}")

            # If this file doesn't already exist in the output directory,
            # then this is easy: we only need to copy it over.
            output_file = os.path.join(output_path, f"pmid-{pmid}.json")
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                with open(output_file, 'w') as f:
                    json.dump(entry, f, sort_keys=True)
                logging.info(f"Copied entry to {output_file}")

            else:
                # Otherwise, we need to merge our entry with the provided entry.
                with open(output_file, 'r') as fin:
                    merge_with = json.load(fin)

                logging.info(f"Merging entry with existing {output_file}")

                # Make sure the source_url and codes are identical.
                assert source_url == merge_with['source_url']
                assert entry['text'] == merge_with['text']

                # Compare tracks.
                tracks = entry['tracks']
                merge_with_tracks = merge_with['tracks']
                merge_with_tracks_projects = set(map(lambda t: t['project'], merge_with_tracks))

                flag_modified = False
                for track in tracks:
                    project = track['project']

                    if project in merge_with_tracks_projects:
                        logging.warning(f"Track '{project}' already exists, not merging.")
                    else:
                        merge_with['tracks'].append(track)
                        logging.info(f"Adding track '{project}', not present in the original.")
                        flag_modified = True

                if flag_modified:
                    logging.info(f"Updated entry, writing back to {output_file}")
                    with open(output_file, 'w') as f:
                        json.dump(entry, f, sort_keys=True)

@click.command()
@click.argument('input', nargs=-1, type=click.Path(
    file_okay=True,
    dir_okay=True,
    exists=True
))
@click.option('--output', '-O', required=True, type=click.Path(
    file_okay=False,
    dir_okay=True,
    exists=False
))
def merge(input, output, **kwargs):
    """
    merge.py [files or directories containing JSONL files to merge]
    """
    output_path = click.format_filename(output)

    for inp in input:
        input_path = click.format_filename(inp)

        if os.path.isdir(input_path):
            # TODO: make this better.
            logging.info(f"Globbing: {f'{input_path}/**/*.jsonl'}.")
            for filename in glob.iglob(f'{input_path}/**/*.jsonl', recursive=True):
                merge_file(filename, output_path)
        else:
            merge_file(input_path, output, kwargs)


if __name__ == '__main__':
    merge()
