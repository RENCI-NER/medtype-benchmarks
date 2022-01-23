#!/usr/bin/python3

#
# PubMedDS to PubAnnotator converter
# This script converts a PubMedDS input file to a PubAnnotator file.
# - PubMedDS: https://doi.org/10.5281/zenodo.5755155
# - PubAnnotator: http://www.pubannotation.org/docs/annotation-format/
#

import click
import json
import logging

logging.basicConfig(level=logging.INFO)

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
def convert(input, output):
    """
    Convert INPUT (a PubMed DS file) into PubAnnotator.
    """

    with click.open_file(output, mode='w') as outp:
        with click.open_file(input) as inp:
            lines = inp.readlines()
            for index, line in enumerate(lines):
                abstract = json.loads(line)

                annotator = {
                    'source_db': 'PubMed',
                    'source_url': f"https://pubmed.ncbi.nlm.nih.gov/{abstract['_id']}/",
                    'project': 'PubMedDS',
                    'text': abstract['text'],
                    'denotations': abstract['mentions']
                }

                json.dump(annotator, outp, indent=4, sort_keys=True)
                outp.write("\n")


if __name__ == '__main__':
    convert()
