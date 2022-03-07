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
@click.option('--url', help='URL of MedType server', default='http://localhost:8125/run_linker', type=str, show_default=True)
@click.option('--entity-linker', help='Entity linker to use', default='scispacy', type=str, show_default=True)
def query_medtype(input, output, url, entity_linker):
    """
    query_medtype.py [PubAnnotator JSONL file to annotate] [directory to write outputs to]
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
        if os.path.exists(raw_output_path):
            logging.info(f'Raw output for PMID {pmid} already exists, skipping. (#{count_done})')
            count_skipped += 1
            continue

        # Submit text to MedType and get response
        response = requests.post(url, json={
            'id': f'PMID:{pmid}',
            'data': {
                'text': [entry['text']],
                'entity_linker': entity_linker
            }
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
            pubannotator_path = os.path.join(output_path, f'pmid-{pmid}.jsonl')
            with open(pubannotator_path, 'w') as f_pubannotator:
                if len(result['result']['elinks']) == 0:
                    logging.warning(f"No results found for PMID {pmid}, skipping.")
                    continue
                elif len(result['result']['elinks']) > 1:
                    raise RuntimeError(f"Too many results ('elinks') found for PMID {pmid}: {json.dumps(result['result']['elinks'], indent=4, sort_keys=True)}")

                global mention_count
                mention_count = 0
                def mentions_to_denotations(mention):
                    global mention_count
                    mention_count += 1

                    filtered_candidates = list(map(lambda fc: fc[0], mention['filtered_candidates']))

                    return {
                        'id': f"D{mention_count}",
                        'link_ids': filtered_candidates,
                        'obj': mention['pred_type'],
                        'span': {
                            'begin': mention['start_offset'],
                            'end': mention['end_offset']
                        },
                        'text': mention['mention']
                    }

                medtype_denotations = {
                    'project': 'MedType-default-2022feb7',
                    'denotations': list(map(mentions_to_denotations, result['result']['elinks'][0]['mentions']))
                }

                pubannotator_entry = entry
                if not isinstance(pubannotator_entry['tracks'], list):
                    pubannotator_entry['tracks'] = [pubannotator_entry['tracks']]
                pubannotator_entry['tracks'].append(medtype_denotations)
                json.dump(pubannotator_entry, f_pubannotator)

            # What rate are we going at?
            count_processed = count_done - count_skipped
            time_processed_secs = (time.time_ns() - time_started)/1E9

            processed_per_second = count_processed/time_processed_secs

            logging.info(f"Raw MedType output written to {raw_output_path}. (#{count_done}, {1/processed_per_second:.3f} seconds/entry)")


if __name__ == '__main__':
    query_medtype()
