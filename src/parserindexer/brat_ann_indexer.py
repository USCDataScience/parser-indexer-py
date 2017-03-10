from solr import Solr
import os, sys
from argparse import ArgumentParser
from indexer import parse_lpsc_from_path

class BratAnnIndexer():

    def parse_ann_line(self, ann_line):
        '''
        parses each annotation line
        '''
        parts = ann_line.strip().split('\t')
        res = {
            'annotation_id_s': parts[0],
            'source': 'brat',
        }
        if parts[0][0] == 'T': # anchors (for targets, components, events)
            args = parts[1].split()[1:]
            res.update({
                'mainType': 'anchor',
                'type': parts[1].split()[0],
                'span_start': args[0],
                'span_end': args[-1],
                'name': parts[2]
            })
        elif parts[0][0] == 'E': # event
            args = parts[1].split()
            subargs = [a.split(':') for a in args[1:]]
            res.update({
                'mainType' : 'event',
                'type'   : args[0].split(':')[0],
                'anchor_s'  : args[0].split(':')[1],
                'targets_ss' : [v for (t,v) in subargs if t.startswith('Targ')],
                'cont_ss'    : [v for (t,v) in subargs if t.startswith('Cont')]
            })

        elif parts[0][0] == 'R': # relation
            label, arg1, arg2 = parts[1].split() # assumes 2 args
            res.update({
                'mainType' : 'relation',
                'type': label,
                'arg1_s': arg1.split(':')[1],
                'arg2_s': arg2.split(':')[1]
            })

        elif parts[0][0] == 'A': # attribute
            label, arg, value = parts[1].split()
            res.update({
                'mainType': 'attribute',
                'type': label,
                'arg1_s': arg,
                'value_s': value
            })
        else:
            print 'Unknown annotation type:', parts[0]
            return None
        res['type'] = res['type'].lower()
        res['_path'] = '/%s' % res['type']
        res['_depth'] = 1
        return res

    def read_records(self, in_file):
        with open(in_file) as inp:
            for line in inp: # assumption: input file is a csv having .txt,.ann paths
                txt_f, ann_f = line.strip().split(',')
                doc_id, doc_year, doc_url = parse_lpsc_from_path(ann_f)
                if doc_id:
                    ann_f.split('/')[-1].replace('.ann', '')

                with open(txt_f) as txtp:
                    txt = txtp.read()
                with open(ann_f) as annp:
                    anns = list(map(self.parse_ann_line, annp.readlines()))
                    children = []
                    for i, ann in enumerate(filter(lambda x: x is not None, anns)):
                        ann['id'] = '%s_%s_%s_%d' % (doc_id, ann['source'], ann['type'], i)
                        ann['p_id'] = doc_id
                        children.append(ann)
                yield {
                    'id' : doc_id,
                    'content_ann_s': {'set': txt},
                    'type': {'set': 'doc'},
                    'url' : {'set': doc_url},
                    'year': {'set': doc_year}
                }
                for child in children:
                    yield child

    def index(self, solr_url, in_file):
        solr = Solr(solr_url)
        recs = self.read_records(in_file)
        count, success, = solr.post_iterator(recs)
        if success:
            print("Indexed %d docs" % count)
        else:
            print("Error: Failed. Check solr logs")


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('-i', '--in', help="Path to input csv file having .txt,.ann records", required=True)
    ap.add_argument('-s', '--solr-url', help="Solr URL", default="http://localhost:8983/solr/docs")
    args = vars(ap.parse_args())
    BratAnnIndexer().index(solr_url=args['solr_url'], in_file = args['in'])
