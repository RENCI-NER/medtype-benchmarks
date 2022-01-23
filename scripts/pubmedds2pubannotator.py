#!/usr/bin/python3

#
# PubMedDS to PubAnnotator converter
# This script converts a PubMedDS input file to a PubAnnotator file.
# - PubMedDS: https://doi.org/10.5281/zenodo.5755155
# - PubAnnotator: http://www.pubannotation.org/docs/annotation-format/
#

import click
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
), help='Where to write PubAnnotator file.')
def convert(input, output):
    """
    Convert INPUT (a PubMed DS file) into PubAnnotator.
    :param input: A PubMed DS file.
    :param output: A PubMed Annotator file.
    :return: Exit code.
    """
    logging.info(f"Converting input {input} to {output}")


if __name__ == '__main__':
    convert()
