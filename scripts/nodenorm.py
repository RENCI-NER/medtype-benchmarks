#!/usr/bin/python3

#
# Node Normalization script
# Given a PubAnnotator input file and a track name, this script will create an additional track called
# "<track name>+NodeNorm" which runs (one or more) matching entities with the Node Normalization service.
#
import os

import glob
import requests
import click
import functools
import json
import logging

logging.basicConfig(level=logging.INFO)


# Look up terms on the Node Normalization service.
@functools.cache
def get_normalized_term(curie):
    response = requests.get('https://nodenormalization-sri.renci.org/1.2/get_normalized_nodes', params={
        'curie': curie
    })
    if not response.ok:
        logging.error("Could not look up MeSH {mesh_id} on the Node Normalization Service, skipping: {response}")
        return {}

    return response.json()


def normalize_entry(filename, output_path, track, first):
    with open(filename, 'r') as f:
        for (index, line) in enumerate(f):
            if line.strip() == '':
                continue
            entry = json.loads(line)
            logging.info(f"{filename} line {index}: {entry}")

            # Write the entry into the output file.
            if entry['source_url'].startswith('https://pubmed.ncbi.nlm.nih.gov/'):
                pmid = entry['source_url'][32:]
                if pmid.endswith('/'):
                    pmid = pmid[:-1]
            else:
                raise RuntimeError(f"Could not parse source ID: {entry['source_url']}")

            # Write to output.
            with open(os.path.join(output_path, f"pmid_{pmid}.jsonl"), "w") as fout:
                json.dump(entry, fout)


@click.command()
@click.argument('input', default='-', type=click.Path(
    file_okay=True,
    dir_okay=True,
    readable=True,
    allow_dash=True
))
@click.option('--output-dir', '-O', default='-', type=click.Path(
    file_okay=False,
    dir_okay=True,
    writable=True,
    allow_dash=True
), help='Directory to write output files to')
@click.option('--track', '-t', help='The track to normalize')
@click.option('--first', is_flag=True, help='Only convert the first entity ID')
def nodenorm(input, output_dir, track, first):
    """
    Given a PubAnnotator input file and a track name, this script will create an additional track called
    'track+NodeNorm' with original track node normalized.
    """

    input_path = click.format_filename(input)
    output_path = click.format_filename(output_dir)

    # logging.info(f"Globbing: {f'{input_path}/**/*.jsonl'}.")

    if os.path.isdir(input_path):
        # TODO: make this better.
        for filename in glob.iglob(f'{input_path}/**/*.jsonl', recursive=True):
            normalize_entry(filename, output_path, track, first)
    else:
        normalize_entry(input_path, output_path, track, first)


if __name__ == '__main__':
    nodenorm()
