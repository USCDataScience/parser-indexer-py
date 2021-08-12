#!/usr/bin/env python
# json2brat.py
# Convert JSON output (from CoreNLP) to brat (.ann) format.
# Brat format: http://brat.nlplab.org/standoff.html 
#
# Kiri Wagstaff
# July 31, 2017

import sys, os, shutil, io
import json
from ioutils import read_jsonlines

def usage():
    print './json2brat.py <JSON file> <output dir>'
    print ' Note: all documents in the JSON file will be'
    print ' saved out to individual files in the output directory.'
    sys.exit(1)

# Merge adjacent words into entities:
# - adjacent Target words found to be in a relation
# - Todo: adjacent Element, Mineral, or Property words in a relation
def merge_adjacent(rels):
    """
    # Nothing to merge
    >>> merge_adjacent([{'target_ids': ['target_1_4'], 'target_names': ['Big'], \
                         'cont_ids': ['element_30_32'], 'cont_names': ['Ca']}])
    [{'cont_ids': ['element_30_32'], 'target_names': ['Big'], 'target_ids': ['target_1_4'], 'cont_names': ['Ca']}]

    # Merge Big + Bob -> Big Bob
    >>> merge_adjacent([{'target_ids': ['target_1_4'], 'target_names': ['Big'], \
                         'cont_ids': ['element_30_32'], 'cont_names': ['Ca']}, \
                        {'target_ids': ['target_5_8'], 'target_names': ['Bob'], \
                         'cont_ids': ['element_30_32'], 'cont_names': ['Ca']}])
    [{'cont_ids': ['element_30_32'], 'target_names': ['Big Bob'], 'target_ids': ['target_1_8'], 'cont_names': ['Ca']}]

    # Merge Big + Bob -> Big Bob with two different components
    >>> merge_adjacent([{'target_ids': ['target_1_4'], 'target_names': ['Big'], \
                         'cont_ids': ['element_30_32'], 'cont_names': ['Ca']}, \
                        {'target_ids': ['target_5_8'], 'target_names': ['Bob'], \
                         'cont_ids': ['element_40_42'], 'cont_names': ['Fl']}])
    [{'cont_ids': ['element_40_42', 'element_30_32'], 'target_names': ['Big Bob'], 'target_ids': ['target_1_8'], 'cont_names': ['Ca', 'Fl']}]
    """

    rels = list(rels)
    #print(len(rels))
    #print(rels)
    change = True
    while change:
        change = False
        #print([r['target_ids'] for r in rels])
        for i in range(len(rels) - 1):
            tids = rels[i]['target_ids']
            # jSRE only returns one target per relation,
            # so we blindly index lists to 0 in several places
            assert(len(tids) == 1)
            start = int(tids[0].split('_')[1])
            end = int(tids[0].split('_')[2])
            next_start = int(rels[i+1]['target_ids'][0].split('_')[1])
            next_end = int(rels[i+1]['target_ids'][0].split('_')[2])
            if end + 1 == next_start:
                merged_target_id = '_'.join(tids[0].split('_')[:2] + [str(next_end)])
                rels[i]['target_ids'] = [merged_target_id]
                rels[i]['target_names'] = [rels[i]['target_names'][0] + ' ' +
                                           rels[i+1]['target_names'][0]]
                #print('merged: ', rels[i]['target_ids'])
                #print(' ', rels[i]['target_names'])
                # Pick up any different components
                rels[i]['cont_ids'].extend(rels[i+1]['cont_ids'])
                rels[i]['cont_ids'] = list(set(rels[i]['cont_ids']))
                rels[i]['cont_names'].extend(rels[i+1]['cont_names'])
                rels[i]['cont_names'] = list(set(rels[i]['cont_names']))
                #print(' cont ids: ', rels[i]['cont_ids'])
                #print(' cont names: ', rels[i]['cont_names'])
                # Remove the second one
                rels.remove(rels[i + 1])
                #print(rels)
                #raw_input()
                change = True
    return rels


def convert_json_to_brat(jsonfile, outdir):
    # Read in the JSON file
    docs = read_jsonlines(jsonfile)

    # Iterate over documents
    for d in docs:
        res_name = d['metadata']['resourceName']
        if type(res_name) == list:
            # Sometimes Tika returns this as something like
            # "resourceName": ["2005_1725.pdf", "High Quality.joboptions"]
            res_name = res_name[0]
        #if res_name[:-4] != '2006_2040':
        #    continue

        # Output text into a .txt file
        text = d['content_ann_s']
        outfn = os.path.join(outdir, res_name[:-4] + '.txt')
        with io.open(outfn, 'w', encoding='utf8') as outf:
            print('Writing text to %s' % outfn)
            outf.write(text + '\n')

        if 'ner' not in d['metadata']:
            print('No named entities found for %s' % d['file'])
            continue

        # Output relevant annotations into a brat .ann file
        outfn = os.path.join(outdir, res_name[:-4] + '.ann')
        outf = io.open(outfn, 'w', encoding='utf8')
        print('Writing annotations to %s' % outfn)

        # Output named entities
        ners = d['metadata']['ner']
        # Create a dict so we can look up arguments by span
        # when outputting relations
        ner_dict = {}
        for (t, n) in enumerate(ners):
            outf.write(u'T%d\t%s %s %s\t%s\n' %
                       (t+1, n['label'], n['begin'], n['end'], n['text']))
            # We are just matching on the starting span,
            # because relation ids use only the first word's span
            # but 'end' here includes multi-word entities
            ner_id = '%s_%s' % (n['label'].lower(), n['begin'])
            #print(ner_id, t+1, n['text'])
            ner_dict[ner_id] = t+1

        # Output relations
        rels = d['metadata']['rel']
        # Merge adjacent relation words into relation entities
        rels = merge_adjacent(rels)
        for r_id, r in enumerate(rels):
            # Currently these are specific to the "contains" relation
            for t in r['target_ids']:
                for c in r['cont_ids']:
                    # Use only the start of the span
                    t = '_'.join(t.split('_')[:2])
                    c = '_'.join(c.split('_')[:2])
                    outf.write(u'R%d\tContains Arg1:T%d Arg2:T%d\n' % 
                               (r_id, ner_dict[t], ner_dict[c]))
                               
        outf.close()


def main():
    if len(sys.argv) != 3:
        usage()

    if not os.path.exists(sys.argv[1]):
        print 'Error: could not find JSON input file %s.' % sys.argv[1]
        usage()

    if not os.path.exists(sys.argv[2]):
        print 'Creating output directory %s.' % sys.argv[2]
        os.mkdir(sys.argv[2])
    else:
        print 'Removing prior output in %s.' % sys.argv[2]
        shutil.rmtree(sys.argv[2])
        os.mkdir(sys.argv[2])

    convert_json_to_brat(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
