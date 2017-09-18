#!/usr/bin/env python
# json2csv.py
# Convert JSON output (from parse_all.py/CoreNLP) to .csv format
# to enable manual review of extracted relations.
#
# Kiri Wagstaff
# August 28, 2017

import sys, os, shutil
import json
from ioutils import read_jsonlines
from progressbar import ProgressBar, ETA, Bar, Percentage

def usage():
    print './json2csv.py <JSON file>'
    sys.exit(1)


def convert_json_to_csv(jsonfile):
    # Get the number of lines (docs) to process
    # Do this before re-opening the file because read_jsonlines()
    # returns a generator.
    with open(jsonfile) as f:
        l = f.readlines()
        ndocs = len(l)
        f.close()

    # Read in the JSON file 
    docs = read_jsonlines(jsonfile)

    # Open the output CSV file
    outfn = jsonfile[:jsonfile.rfind('.')] + '.csv'
    outf = open(outfn, 'w')
    print 'Writing to', outfn
    # Header
    outf.write('Judgment, Docid, Target, Component, Sentence\n')

    widgets = ['Docs (of %d): ' % ndocs, Percentage(), ' ', 
               Bar('='), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=ndocs).start()
    # Iterate over documents
    i=1
    for d in docs:
        if 'rel' not in d['metadata']:
            continue

        docid = d['metadata']['resourceName']

        # Output relations into the .csv file
        rels = d['metadata']['rel']
        ners = d['metadata']['ner']
        skip_inds = []
        for (t, r) in enumerate(rels):
            # Special merging step for adjacent Target tokens
            # If this matches a multi-word NER,
            # expand the target name and skip the next relation
            start_target = int(r['target_ids'][0].split('_')[1])
            end_target   = int(r['target_ids'][0].split('_')[2])
            # These are arrays, but for auto-annotations,
            # they will only ever have one item
            targ_name    = r['target_names'][0]
            cont_name    = r['cont_names'][0]

            if start_target in skip_inds:
                continue
            next_rels = [r2 for r2 in rels if
                         int(r2['target_ids'][0].split('_')[1]) > end_target]
            if len(next_rels) > 0:
                next_rels.sort(key=lambda x: 
                               int(x['target_ids'][0].split('_')[1]))
                next_rel = next_rels[0]
                start_next_target = int(next_rel['target_ids'][0].split('_')[1])
                end_next_target   = int(next_rel['target_ids'][0].split('_')[2])
                ner_matches = [n for n in ners if \
                               n['text'].startswith(targ_name) and
                               n['begin'] == start_target and
                               n['end'] == end_next_target]
                if len(ner_matches) > 0:
                    print('Merging %s and %s' % (targ_name,
                                                 next_rel['target_names'][0]))
                    targ_name += ' ' + next_rel['target_names'][0]
                    skip_inds.append(start_next_target)

            # If cont_name is something like Fe-rich or Mg_sulfate,
            # only keep the first bit.
            if '-' in cont_name:
                cont_name = cont_name[:cont_name.find('-')]
            elif '_' in cont_name:
                cont_name = cont_name[:cont_name.find('_')]

            outf.write(',%s,%s,%s,"%s"\n' % 
                       (docid,
                        #r['target_names'][0],
                        targ_name,
                        cont_name,
                        r['sentence']))
                       # build URL manually? 
        pbar.update(i)
        i += 1

    print
    outf.close()


def main():
    if len(sys.argv) != 2:
        usage()

    if not os.path.exists(sys.argv[1]):
        print 'Error: could not find JSON input file %s.' % sys.argv[1]
        usage()

    convert_json_to_csv(sys.argv[1])


if __name__ == '__main__':
    main()
