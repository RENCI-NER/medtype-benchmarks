#!/usr/bin/python3

#
# PubMedDS to PubAnnotator converter
# This script converts a PubMedDS input file to a PubAnnotator file.
# - PubMedDS: https://doi.org/10.5281/zenodo.5755155
# - PubAnnotator: http://www.pubannotation.org/docs/annotation-format/
#

import requests
import click
import functools
import json
import logging

logging.basicConfig(level=logging.INFO)

# Look up abstracts on PubAnnotator via PubMed IDs.
@functools.cache
def get_pubannotations(pubmed_id):
    response = requests.get(f'https://pubannotation.org/docs/sourcedb/PubMed/sourceid/{pubmed_id}/annotations.json')
    if not response.ok:
        logging.error(f"Could not look up PubMed ID {pubmed_id} on PubAnnotator: {response}")
        return []

    result = response.json()
    if not 'tracks' in result:
        return []
    return result['tracks']

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


@click.command()
@click.argument('input', default='-', type=click.Path(
    file_okay=True,
    dir_okay=False,
    readable=True,
    allow_dash=True
))
@click.option('--output', '-O', default='-', type=click.Path(
    file_okay=True,
    dir_okay=False,
    writable=True,
    allow_dash=True
), help='PubAnnotator file to create (either JSON or JSONL, depending on the number of input texts)')
@click.option('--normalize', is_flag=True, default=False, help='Use the RENCI Node Normalization service to normalize terms')
@click.option('--pubannotation', is_flag=True, default=False, help='Include the PubAnnotation annotations as well.')
def convert(input, output, normalize, pubannotation):
    """
    Convert INPUT (a PubMed DS file) into PubAnnotator.
    """

    with click.open_file(output, mode='w') as outp:
        with click.open_file(input) as inp:
            lines = inp.readlines()
            for index, line in enumerate(lines):
                abstract = json.loads(line)

                denotation_count = 0
                annotations = []

                def translate_mention(mention, normalize=False):
                    """ Translates a PubMedDS mention into a PubAnnotator denotation. """

                    mesh_id = mention['mesh_id']
                    link_ids = mention['link_id'].split('|')

                    nonlocal denotation_count
                    denotation_count += 1
                    denotation_id = f'D{denotation_count}'

                    denotation = {
                        'id': denotation_id,
                        'obj': mesh_id,
                        'span': {
                            'begin': mention['start_offset'],
                            'end': mention['end_offset']
                        },
                        # These fields are not standard PubAnnotator fields, but are convenient for our needs.
                        'link_ids': link_ids,
                        'text': mention['mention']
                    }

                    if normalize:
                        curie = f'MESH:{mesh_id}'
                        json = get_normalized_term(curie)

                        if curie not in json:
                            logging.warning(f'No results found for {curie} on the Node Normalization service, skipping: {json}')
                        else:
                            denotation['obj'] = json[curie]['id']['identifier']
                            denotation['label'] = json[curie]['id']['label']
                            denotation['types'] = json[curie]['type']

                    # TODO: we can also translate the MeSH ID into a MeSH Tree Number, which can give us a top-level
                    # concept ID. There aren't an infinite number of these.
                    # e.g. 'thalidomide' (https://id.nlm.nih.gov/mesh/D013792.html) -> D03.383.621.808.800, D03.633.100.513.750.750, D02.241.223.805.810.800
                    # D03 = http://id.nlm.nih.gov/mesh/D03 = https://id.nlm.nih.gov/mesh/D006571.html ("Heterocyclic Compounds")
                    # D02 = http://id.nlm.nih.gov/mesh/D02 = https://id.nlm.nih.gov/mesh/D009930.html ("Organic Compounds")

                    return denotation

                pubmed_id = abstract['_id']

                annotator = {
                    'source_db': 'PubMed',
                    'source_url': f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                    'project': 'PubMedDS',
                    'text': abstract['text'],
                    'tracks': [{
                        'project': 'PubMedDS',
                        'denotations': list(map(translate_mention, abstract['mentions']))
                    }]
                }

                if normalize:
                    annotator['tracks'].push({
                        'project': 'PubMedDS+NodeNormalization',
                        'denotations': list(map(lambda m: translate_mention(m, normalize=True), abstract['mentions']))
                    })

                if pubannotation:
                    annotations = get_pubannotations(pubmed_id)
                    if annotations:
                        annotator['tracks'].extend(annotations)

                json.dump(annotator, outp, indent=4, sort_keys=True)
                outp.write("\n")


if __name__ == '__main__':
    convert()
