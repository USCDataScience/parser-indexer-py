#!/usr/bin/env python
# 
# Read in MTE extractions (.jsonl) and align with expert-vetting (.csv)
# to filter; write out only those marked 'Y' by expert to new .jsonl.
#
# Author: Kiri Wagstaff
# June 10, 2018
# Copyright notice at bottom of file.

import sys, os
from ioutils import read_jsonlines, dump_jsonlines
import codecs, csv

def read_extractions(extractions):
    # Get the number of lines (docs) to process
    # Do this before re-opening the file because read_jsonlines()
    # returns a generator.
    with open(extractions) as f:
        l = f.readlines()
        ndocs = len(l)
        f.close()

    # Read in the JSON file (contains, among other things, extractions)
    docs = read_jsonlines(extractions)

    return docs, ndocs


# Read in the expert annotations (.csv)
def read_expert(expert):
    judgments = []
    #nrows = 0
    with codecs.open(expert, 'r', 'UTF-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            judgments.append(row)
            #nrows += 1
            #if row['Judgment'] == 'Y':
            #    approved.append(row)
    #print len(approved), 'of', nrows, 'relations approved.'
    print 'Read %d judgments.' % len(judgments)

    return judgments


def query_relation(target, cont, sentence):
    print('<%s> contains <%s>? [y/n]' % (target, cont))
    print('Sentence: <%s>' % sentence)

    return raw_input()


def main(extractions, expert, outfile):

    # Check arguments
    if not os.path.exists(extractions):
        print('Could not find extractions file %s.' % extractions)
        sys.exit(1)

    if not os.path.exists(expert):
        print('Could not find expert file %s.' % expert)
        sys.exit(1)

    # Read in the JSON file (contains, among other things, extractions)
    docs, ndocs = read_extractions(extractions)
    filtered_docs = []

    # Read in the expert annotations (.csv)
    judgments = read_expert(expert)

    # Align them.  Iterate over the documents.
    n_rels_keep  = 0
    n_rels_total = 0
    for (i,d) in enumerate(docs):
        # If there are no relations, omit this document
        if 'rel' not in d['metadata']:
            continue

        docid = d['metadata']['resourceName']
        rels  = d['metadata']['rel']
        n_rels_total += len(rels)

        doc_judgments = [j for j in judgments if j[' Docid'] == docid]

        # Relations to keep
        filtered_rels = []

        if len(doc_judgments) == len(rels):
            # Same number in each set, so we can zip them up
            for (r, j) in zip(rels, doc_judgments):
                # Can't do exact string match on target_name because 
                # some are partials.
                # Can't do exact string match on cont_name because 
                # I helpfully expanded element names in the expert file.
                # Can do match on sentence at least!
                if (r['target_names'][0] == j[' Target'] and
                    #r['cont_names'][0]   == j[' Component'] and
                    r['sentence']        == j[' Sentence']):
                    # Only keep items judged 'Y'
                    if j['Judgment'] == 'Y':
                        filtered_rels.append(r)
                else:
                    # Mismatch, so drop into manual review mode
                    res = query_relation(r['target_names'][0], 
                                         r['cont_names'][0],
                                         r['sentence'])
                    if res == 'y' or res == 'Y':
                        filtered_rels.append(r)
        else:
            # Different number of relations in expert vs. system output
            # so time for manual review
            print('%d/%d: ****** MANUAL REVIEW MODE (%s) ******' % \
                      (i, ndocs, docid))
            for r in rels:
                res = query_relation(r['target_names'][0], 
                                     r['cont_names'][0],
                                     r['sentence'])
                if res == 'y' or res == 'Y':
                    filtered_rels.append(r)
                    
        print('%s (%d/%d): Kept %d/%d relations.' % \
                  (docid, i, ndocs, len(filtered_rels), len(rels)))

        # Only save this document if it has relations remaining
        if len(filtered_rels) > 0:
            n_rels_keep += len(filtered_rels)
            d['metadata']['rel'] = filtered_rels
            filtered_docs.append(d)

    # Save filtered JSON content to outfile
    dump_jsonlines(filtered_docs, outfile)
    print
    print('Kept %d/%d relations in %d/%d documents.' % \
              (n_rels_keep, n_rels_total,
               len(filtered_docs), ndocs))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)

    parser.add_argument('extractions', help='.jsonl file containing all NER and RE extractions')
    parser.add_argument('expert',      help='.csv file containing expert judgment of all relations')
    parser.add_argument('outfile',     help='.jsonl file to store filtered extractions')

    args = parser.parse_args()

    main(**vars(args))


# Copyright 2018, by the California Institute of Technology. ALL
# RIGHTS RESERVED. United States Government Sponsorship
# acknowledged. Any commercial use must be negotiated with the Office
# of Technology Transfer at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws and
# regulations.  By accepting this document, the user agrees to comply
# with all applicable U.S. export laws and regulations.  User has the
# responsibility to obtain export licenses, or other export authority
# as may be required before exporting such information to foreign
# countries or providing access to foreign persons.
