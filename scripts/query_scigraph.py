#!/usr/bin/env python3

# This script goes through a PubAnnotator file, sends the text to MedType, and adds annotations
# back to the PubAnnotator file.

import logging
import json
import os
import time

import click
import requests

logging.basicConfig(level=logging.INFO)


@click.command()
@click.argument('input', type=click.File('r'))
@click.argument('output', type=click.Path(
    file_okay=False,
    dir_okay=True
))
# TODO: add includeCat and excludeCat
@click.option('--url', help='URL of SciGraph server',
              default='https://scigraph.apps.renci.org/scigraph/annotations/entities', type=str, show_default=True)
@click.option('--min-length', help='Minimum length of terms to search for', default='3', type=int, show_default=True)
@click.option('--longest-only', help='Only return the longest term', default='false', type=str, show_default=True)
@click.option('--include-abbreviation', help='Include abbreviations', default='true', type=str, show_default=True)
@click.option('--include-acronym', help='Include acronyms', default='true', type=str, show_default=True)
@click.option('--include-numbers', help='Include numbers', default='true', type=str, show_default=True)
def query_scigraph(input, output, url, min_length, longest_only, include_abbreviation, include_acronym, include_numbers):
    """
    query_scigraph.py [PubAnnotator JSONL file to annotate] [directory to write outputs to]
    """
    output_path = click.format_filename(output)

    # Look through JSONL input file.
    count_done = 0
    count_skipped = 0
    time_started = time.time_ns()
    for line in input:
        entry = json.loads(line)
        logging.debug(f"Loaded entry: {json.dumps(entry, sort_keys=True, indent=4)}")

        # Get PMID.
        source_url = entry['source_url']
        if source_url.startswith('https://pubmed.ncbi.nlm.nih.gov/'):
            pmid = source_url[32:]
            if pmid.endswith('/'):
                pmid = pmid[:-1]
        else:
            raise RuntimeError(f'Could not identify PubMed ID for source_url {source_url}')

        # Increment count
        count_done += 1

        # Does the raw file already exist?
        raw_output_path = os.path.join(output_path, f'raw-pmid-{pmid}.json')
        pubannotator_path = os.path.join(output_path, f'pmid-{pmid}.jsonl')
        if os.path.exists(pubannotator_path):
            logging.info(f'PubAnnotator output for PMID {pmid} already exists, skipping. (#{count_done})')
            count_skipped += 1
            continue

        # Submit text to MedType and get response
        text = entry.get('text', '')
        response = requests.post(url, data={
            'content': text,
            'min_length': min_length,
            'longest_only': longest_only,
            'include_abbreviation': include_abbreviation,
            'include_acronyms': include_acronym,
            'include_numbers': include_numbers
        })
        if not response.ok:
            logging.error(f"Error occurred for PMID {pmid}, skipping.")
        else:
            result = response.json()
            logging.info(f"Entities for PMID {pmid}: {json.dumps(result, sort_keys=True, indent=4)}")

            # To simplify future runs, let's write out the raw MedType output first.
            with open(raw_output_path + '.in-process', 'w') as f:
                json.dump(result, f, sort_keys=True, indent=4)

            os.rename(raw_output_path + '.in-process', raw_output_path)

            # Let's write out results in PubAnnotator format.
            with open(pubannotator_path, 'w') as f_pubannotator:
                global mention_count
                mention_count = 0

                def scigraph_result_to_denotations(r):
                    global mention_count
                    mention_count += 1

                    if 'token' not in r:
                        raise RuntimeError(f"Result missing a token: {json.dumps(r)}")

                    start = r['start']
                    end = r['end']
                    span = text[start:end]
                    id = r['token']['id']
                    categories = r['token'].get('categories', [])
                    terms = r['token'].get('terms', [])

                    logging.info(f"Found '{span}' {id} ({terms}) [{categories}]")

                    return {
                        'id': f"D{mention_count}",
                        'link_ids': [id],
                        'obj': categories,
                        'span': {
                          'begin': r['start'],
                          'end': r['end']
                        },
                        'text': span,
                        'terms': terms
                    }

                scigraph_denotations = {
                    'project': 'SciGraph on Sterling, 2022apr30',
                    'denotations': list(map(scigraph_result_to_denotations, result))
                }

                pubannotator_entry = entry
                if not isinstance(pubannotator_entry['tracks'], list):
                    pubannotator_entry['tracks'] = [pubannotator_entry['tracks']]
                pubannotator_entry['tracks'].append(scigraph_denotations)
                json.dump(pubannotator_entry, f_pubannotator)

            # What rate are we going at?
            count_processed = count_done - count_skipped
            time_processed_secs = (time.time_ns() - time_started) / 1E9

            processed_per_second = count_processed / time_processed_secs

            logging.info(
                f"Raw SciGraph output written to {raw_output_path}. (#{count_done}, {1 / processed_per_second:.3f} seconds/entry)")


if __name__ == '__main__':
    query_scigraph()
