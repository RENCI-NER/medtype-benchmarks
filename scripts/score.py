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


def score_file(input_path, output_file, filter_tracks):
    """ Score an individual file and write it out to the given file. """
    filter_set = set(filter_tracks)
    project_names = set()
    results = {}

    with open(input_path, 'r') as f:
        for line in f:
            # Collect all the denotations that span the same area.
            denotations_by_span = {}

            global conf_limit
            conf_limit -= 1
            if conf_limit < 0:
                break
            logging.debug(f"Scoring {line[:100]}")
            entry = json.loads(line)
            source_url = entry['source_url']

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
                if len(filter_tracks) > 0 and project not in filter_set:
                    continue
                project_names.add(project)
                denotations = track['denotations']
                for denotation in denotations:
                    add_denotation(project, denotation)

            # Some raw information if useful.
            logging.debug("Denotations:")
            for span in denotations_by_span.keys():
                count = len(denotations_by_span[span])
                if count > 1:
                    logging.debug(f" - {span} ({count} annotations):")
                    for den in denotations_by_span[span]:
                        if isinstance(den['obj'], list) and 'biolink:NamedThing' in den['obj']:
                            logging.debug(f"  - [BIOLINK] {den['text']}: {den}")
                        else:
                            logging.debug(f"  - {den['text']}: {den}")

            # Calculate the scores
            # 1. For every track:
            #   1. Calculate how many denotations are shared with every other track.
            for project1 in project_names:
                for project2 in project_names:
                    # Don't compare with itself.
                    if project1 == project2:
                        continue

                    # Set up a result object to write the results to.
                    if project1 not in results:
                        results[project1] = {}
                    if project2 not in results[project1]:
                        results[project1][project2] = {
                            'total_spans': 0,
                            'shared_spans': 0,
                            'spans_in_1_but_not_2': 0,
                            'spans_in_2_but_not_1': 0,
                            'identical_link_ids': 0,
                            'identical_obj': 0
                        }

                    result = results[project1][project2]

                    shared_spans = set()
                    spans_in_1_but_not_2 = set()
                    spans_in_2_but_not_1 = set()

                    for span in denotations_by_span.keys():
                        dens = denotations_by_span[span]
                        den1 = list(filter(lambda d: d['project'] == project1, dens))
                        den2 = list(filter(lambda d: d['project'] == project2, dens))

                        if den1 and den2:
                            shared_spans.add(span)
                        elif den1 and not den2:
                            spans_in_1_but_not_2.add(span)
                        elif not den1 and den2:
                            spans_in_2_but_not_1.add(span)

                    result['total_spans'] += len(shared_spans) + len(spans_in_1_but_not_2) + len(spans_in_2_but_not_1)
                    result['shared_spans'] += len(shared_spans)
                    result['spans_in_1_but_not_2'] += len(spans_in_1_but_not_2)
                    result['spans_in_2_but_not_1'] += len(spans_in_2_but_not_1)

                    # print(f"In file {input_path}, source_url {source_url} between {project1} and {project2}:")
                    # print(f" - Total spans: {len_total_spans}")
                    # print(" - Shared spans: {} ({:.2%})".format(len_shared_spans, float(len_shared_spans)/len_total_spans))
                    # print(" - Spans in 1 but not 2: {} ({:.2%})".format(len_spans_in_1_but_not_2, float(len_spans_in_1_but_not_2)/len_total_spans))
                    # print(" - Spans in 2 but not 1: {} ({:.2%})".format(len_spans_in_2_but_not_1, float(len_spans_in_2_but_not_1)/len_total_spans))

                    # We can't really do any analysis where there isn't overlap, but for shared spans we can compare them.
                    count_linkid_identical = 0
                    count_obj_identical = 0
                    for span in shared_spans:
                        dens = denotations_by_span[span]
                        dens1 = list(filter(lambda d: d['project'] == project1, dens))
                        dens2 = list(filter(lambda d: d['project'] == project2, dens))

                        flag_linkid_match = False
                        flag_obj_match = False

                        for den1 in dens1:
                            den1_linkids = den1['link_ids']
                            for linkid1 in den1_linkids:
                                if flag_linkid_match:
                                    break

                                for den2 in dens2:
                                    if linkid1 in den2['link_ids']:
                                        flag_linkid_match = True
                                        break

                            den1_obj = den1['obj']
                            for obj1 in den1_obj:
                                if flag_obj_match:
                                    break

                                for den2 in dens2:
                                    if obj1 in den2['obj']:
                                        flag_obj_match = True
                                        break

                        if flag_linkid_match:
                            count_linkid_identical += 1

                        if flag_obj_match:
                            count_obj_identical += 1

                    result['identical_link_ids'] += count_linkid_identical
                    result['identical_obj'] += count_obj_identical

                    # print(" - For shared spans:")
                    # print("     - Identical link_ids (item) matches: {} ({:.2%})".format(count_linkid_match, float(count_linkid_match)/len_shared_spans))
                    # print("     - Identical obj (category) matches: {} ({:.2%})".format(count_obj_match, float(count_obj_match)/len_shared_spans))

    # print(json.dumps(results, sort_keys=True, indent=4))
    return results

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

    count_files = 0
    if os.path.isdir(input_path):
        # TODO: make this better.
        results = {}
        for filename in glob.iglob(f'{input_path}/**/*.jsonl', recursive=True):
            count_files += 1
            inner_result = score_file(filename, output, filter)

            # Add this on to the results object.
            for project1 in inner_result.keys():
                if project1 not in results:
                    results[project1] = {}
                for project2 in inner_result[project1].keys():
                    if project2 not in results[project1]:
                        results[project1][project2] = {}
                    for key in inner_result[project1][project2]:
                        if key not in results[project1][project2]:
                            results[project1][project2][key] = 0

                        # The inner result should never cause the total to _decrease_.
                        assert(inner_result[project1][project2][key] >= 0)

                        results[project1][project2][key] += inner_result[project1][project2][key]

            # All of these numbers should be going up over time.
            logging.debug(f"Processing {filename}, results at: {json.dumps(results, indent=2, sort_keys=True)}")

    else:
        results = score_file(input_path, output, filter)
        count_files = 1

    print(f"Counted results from {count_files} files.")
    for project1 in results.keys():
        print(f" - Project 1: {project1}")
        for project2 in results[project1].keys():
            print(f"   - Project 2: {project2}")

            inner_result = results[project1][project2]

            print("     - Total spans across both projects: {}".format(inner_result['total_spans']))
            print("     - Spans in project 1 but not in project 2: {} ({:.2%})".format(inner_result['spans_in_1_but_not_2'], float(inner_result['spans_in_1_but_not_2'])/inner_result['total_spans']))
            print("     - Spans in project 2 but not in project 1: {} ({:.2%})".format(inner_result['spans_in_2_but_not_1'], float(inner_result['spans_in_2_but_not_1'])/inner_result['total_spans']))
            print("     - Shared spans: {} ({:.2%}), of which:".format(inner_result['shared_spans'], float(inner_result['shared_spans'])/inner_result['total_spans']))
            print("       - Identical link_ids (item) matches: {} ({:.2%})".format(inner_result['identical_link_ids'], float(inner_result['identical_link_ids'])/inner_result['shared_spans']))
            print("       - Identical obj (category) matches: {} ({:.2%})".format(inner_result['identical_obj'], float(inner_result['identical_obj'])/inner_result['shared_spans']))


if __name__ == '__main__':
    score()
