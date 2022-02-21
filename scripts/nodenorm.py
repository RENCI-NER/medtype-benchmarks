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

s = requests.Session()
a = requests.adapters.HTTPAdapter(max_retries=10)
s.mount('http://', a)
s.mount('https://', a)

# Look up terms on the Node Normalization service.
@functools.cache
def get_normalized_term(curie):
    response = s.get('https://nodenormalization-sri.renci.org/1.2/get_normalized_nodes', params={
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
            logging.debug(f"{filename} line {index}: {entry}")

            # Write the entry into the output file.
            if entry['source_url'].startswith('https://pubmed.ncbi.nlm.nih.gov/'):
                pmid = entry['source_url'][32:]
                if pmid.endswith('/'):
                    pmid = pmid[:-1]
            else:
                raise RuntimeError(f"Could not parse source ID: {entry['source_url']}")

            # Check for existing output file.
            output_filename = os.path.join(output_path, f"pmid_{pmid}.jsonl")
            if os.path.exists(output_filename):
                logging.info(f"Found output for PMID {pmid}, skipping.")
                continue

            # Look for the expected track.
            tracks = entry['tracks']
            flag_matched_track = False
            for tr in tracks:
                if tr['project'] == track:
                    flag_matched_track = True

                    # Normalize track and write to new_track
                    new_track = {
                        'project': f"{track}+NodeNorm",
                        'denotations': []
                    }

                    denotations = tr['denotations']
                    for denotation in denotations:
                        if not first:
                            raise RuntimeError(f"Only 'first' is currently supported.")
                        else:
                            link_ids = denotation['link_ids']
                            if not link_ids:
                                logging.warning(f"No link_id found in denotation {denotation} in entry {entry}")
                                continue
                            else:
                                link_id = link_ids[0]

                        # TODO: improve very dumb UMLS ID check.
                        if link_id.startswith('C'):
                            link_id = f"UMLS:{link_id}"

                        # Look up link_id via NodeNorm.
                        result = get_normalized_term(link_id)
                        if link_id in result and 'id' in result[link_id] and 'identifier' in result[link_id]['id']:
                            denotation['link_ids'] = [result[link_id]['id']['identifier']]

                            if 'type' in result[link_id]:
                                denotation['obj'] = result[link_id]['type']

                        new_track['denotations'].append(denotation)

                    tracks.append(new_track)

            if not flag_matched_track:
                logging.warning(f"Track '{track}' not found in {filename}")

            # Write to output.
            with open(output_filename + '.in-progress', "w") as fout:
                json.dump(entry, fout)

            os.rename(output_filename + '.in-progress', output_filename)


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
