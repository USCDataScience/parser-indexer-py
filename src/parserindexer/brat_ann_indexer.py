from solr import Solr
import os, sys
reload(sys)
sys.setdefaultencoding('UTF8') # making UTF8 as default encoding
from argparse import ArgumentParser
from indexer import parse_lpsc_from_path
import re
from utils import canonical_name

# Functions to perform reference removal (assumes [n] reference style)
# Written by Karanjeet Singh
def extract_references(content):
    """
    Extract references from text
    :param content: text
    :return: dictionary of references with reference id ([N]) as key
    """
    references = {}
    content = content.replace("\n", "\\n")
    matches = re.findall('(\[[0-9]+\][^\[]*?(?=\[|Acknowledge|Fig|Table|Conclusion|pdf))', content)
    if matches:
        for match in matches:
            ref_id = get_reference_id(match)
            # No reference id exist -- skip it
            if ref_id != -1:
                value = match.replace('\\n', '\n')
                references[ref_id] = value
    return references

def get_reference_id(reference):
    """
    Extract reference id ([N])
    :param reference: Any possible reference
    :return: reference id
    """
    ref_id = -1
    match = re.search('\[[0-9]+\]', reference)
    if match:
        ref_id = int(match.group(0).strip('[]'))
    return ref_id


class BratAnnIndexer():
    '''
    This class reads/parses brat annotations from file system and indexes them
    into Solr.
    '''

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
                'span_start': int(args[0]),
                'span_end': int(args[-1]),
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

    def extract_excerpt(self, content, ann):
        '''
        Extracts excerpt of an annotation from content
        @param content - text content of document
        @param ann annotation having span_start and span_end
        @return excerpt text
        '''
        (anchor_start, anchor_end)= ann['span_start'], ann['span_end']

        # Start: first capital letter after last period before last capital letter!
        sent_start = 0
        # Last preceding capital
        m = [m for m in re.finditer('[A-Z]',content[:anchor_start])]
        if m:
            sent_start = m[-1].start()
        # Last preceding period
        sent_start = max(content[:sent_start].rfind('.'), 0)
        # Next capital
        m = re.search('[A-Z]',content[sent_start:])
        if m:
            sent_start = sent_start + m.start()
        # End: next period followed by {space,newline}, or end of document.
        sent_end     = anchor_end + content[anchor_end:].find('. ')+1
        if sent_end <= anchor_end:
            sent_end = anchor_end + content[anchor_end:].find('.\n')+1
        if sent_end <= anchor_end:
            sent_end = len(content)
        return content[sent_start:sent_end]

    def read_records(self, in_file):
        '''
        Reads brat annotations as solr input documents
        @param in_file Input CSV file having text file and annotation file paths
        '''
        with open(in_file) as inp:
            for line in inp: # assumption: input file is a csv having .txt,.ann paths
                txt_f, ann_f = line.strip().split(',')
                doc_id, doc_year, doc_url = parse_lpsc_from_path(ann_f)
                venue = "LPSC-%d" % doc_year
                if doc_id:
                    ann_f.split('/')[-1].replace('.ann', '')

                with open(txt_f) as txtp:
                    txt = txtp.read()
                with open(ann_f) as annp:
                    anns = list(map(self.parse_ann_line, annp.readlines()))
                    children = []
                    index = {} # index all annotations by its ids
                    for ann in filter(lambda x: x is not None, anns):
                        ann_id = ann['annotation_id_s']
                        ann['id'] = '%s_%s_%s_%s' % (doc_id, ann['source'], ann['type'], ann_id)
                        ann['p_id'] = doc_id
                        index[ann_id] = ann
                        children.append(ann)

                    # resolve references from Events to Targets and Contains
                    contains = filter(lambda a: a.get('mainType') == 'event'\
                                    and a.get('type') == 'contains', children)
                    for ch in contains:
                        targets_anns = ch.get('targets_ss', [])
                        cont_anns = ch.get('cont_ss', [])
                        ch['target_ids_ss'] = list(map(lambda t: index[t]['id'], targets_anns))
                        ch['target_names_ss'] = list(map(lambda t: index[t]['name'], targets_anns))
                        ch['cont_ids_ss'] = list(map(lambda c: index[c]['id'], cont_anns))
                        ch['cont_names_ss'] = list(map(lambda c: index[c]['name'], cont_anns))
                        # extract excerpt from anchor annotation
                        anc_doc = index[ch['anchor_s']]
                        ch['excerpt_t'] = self.extract_excerpt(txt, anc_doc)

                # Extract references
                references = extract_references(txt)

                # Remove references from the content
                for ref_id in references:
                    txt = txt.replace(references[ref_id], ' ' * len(references[ref_id]))

                yield {
                    'id' : doc_id,
                    'content_ann_s': {'set': txt},
                    'references': {'set': references.values()},
                    'type': {'set': 'doc'},
                    'url': {'set': doc_url},
                    'year': {'set': doc_year},
                    'venue': {'set': venue}
                }
                for child in children:
                    if 'name' in child:
                        child['can_name'] = canonical_name(child['name'])
                    if 'target_names_ss' in child:
                        child['target_names_ss'] = map(canonical_name, child['target_names_ss'])
                    if 'cont_names_ss' in child:
                        child['cont_names_ss'] = map(canonical_name, child['cont_names_ss'])
                    yield child

    def index(self, solr_url, in_file):
        '''
        Reads annotations at the specified path and indexes them to solr
        @param solr_url Target Solr URL to index
        @param in_file CSV file having text file and annotation file paths
        '''
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
    ap.add_argument('-s', '--solr-url', help="Solr URL", default="http://localhost:8983/solr/docsdev")
    args = vars(ap.parse_args())
    BratAnnIndexer().index(solr_url=args['solr_url'], in_file = args['in'])
