#!/usr/bin/env python3

# A script for converting PubTator files into PubAnnotator files.

import logging
import json
import glob
import os
import time
import gzip
import re

import click
import requests

logging.basicConfig(level=logging.INFO)

@click.command()
@click.argument('input', type=click.Path(
    exists=True,
    dir_okay=False,
    file_okay=True
))
@click.option('--output', '-O', help='Where to write the output.', default='-', type=click.File('w'))
@click.option('--project', help='The project to write out (defaults to the input filename)', type=str)
def pubtator2pubannotator(input, output, project):
    """
    pubtator2pubannotator.py [PubTator file to convert]
    """

    input_path = click.format_filename(input)
    if not project:
        project = os.path.basename(input_path)

    if input_path.endswith('.gz'):
        file = gzip.open(input_path, 'rt') # rt = read text
    else:
        file = open(input_path, 'r')

    for line in file:
        # We're expecting the |t| line.
        if line.strip() == '':
            continue

        # Read the t-line
        m_t = re.match("^(\\d+)|t|(.*)$", line)
        if not m_t:
            raise RuntimeError(f"Expected title line, found: {line} -- could not parse.")

        pmid = m_t.group(1)
        title = m_t.group(2)

        # Read the a-line
        line = file.readline()
        m_a = re.match("^(\\d+)|a|(.*)$", line)
        if not m_a:
            raise RuntimeError(f"Expected abstract line, found: {line} -- could not parse.")

        if m_a.group(1) != pmid:
            raise RuntimeError(f"Abstract line has a different PMID ({m_a.group(1)} from title line ({pmid}), aborting.")
        abstract = m_a.group(2)

        denotations = []
        denotation_count = 0

        # Read the annotations
        while True:
            line = file.readline()

            if line.strip() == '':
                # An empty line indicates the end of the annotations, break back to the outer loop.
                # Apparently, readline() returns '' once we hit the EOF, so that's convenient for us.
                break

            m_annot = re.match("^(\\d+)\t(\\d+)\t(\\d+)\t(.*)\t(.*)\t(.*)$", line)
            if not m_annot:
                raise RuntimeError(f"Could not parse annotation line: {line}")

            if m_annot.group(1) != pmid:
                raise RuntimeError(f"Annotation line has a different PMID ({m_annot.group(1)}) from the title line ({pmid}), aborting.")

            start_index = m_annot.group(2)
            end_index = m_annot.group(3)
            text = m_annot.group(4)
            categories = m_annot.group(5)
            umls_id = m_annot.group(6)

            denotation_count += 1
            denotations.append({
                'id': f"D{denotation_count}",
                'obj': categories.split(','),
                'span': {
                    'begin': start_index,
                    'end': end_index
                },
                'link_ids': umls_id.split(','),
                'text': text
            })

        # Write out entry
        entry = {
            'source_db': 'PubMed',
            'source_url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            'project': project,
            'text': abstract,
            'tracks': {
                'project': project,
                'denotations': denotations
            }
        }
        output.write(json.dumps(entry))
        output.write('\n')

    file.close()


if __name__ == '__main__':
    pubtator2pubannotator()
