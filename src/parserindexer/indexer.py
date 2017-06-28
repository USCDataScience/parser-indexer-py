from __future__ import print_function
import argparse
from argparse import ArgumentParser
from ioutils import read_jsonlines
from solr import Solr
import sys
import string
import re
from utils import canonical_name, canonical_target_name

# basic map
md_map = {
    # format :
    #   source_field :[copy_field1, copy_field2]
    'Content-Type': ['contentType'],
    'NER_LOCATION': ['locations'],
    'NER_PERSON': ['persons'],
    'NER_ORGANIZATION': ['organizations'],
    'NER_PHONENUMBER': ['phonenumbers'],
    'NER_EMAIL': ['emails']
}

# journals map
grobid_map = {
    'dcterms:created_t_md': 'createdAt',
    'mdcterms:modified_t_md': 'modifiedAt',
    'grobid:header_title_t_md': 'title',
    'grobid:header_authors_t_md': 'authors',
    'grobid:header_affiliation_t_md': 'affiliations_ts_md'
}

lpsc_pattern = re.compile(".*lpsc[-_/]?([0-9]*).*/([0-9]+)\.(?:pdf|ann|txt)", re.I)
def parse_lpsc_from_path(path_str):
    '''
        Constructs ID and LPSC URL from path string
    '''
    m = lpsc_pattern.match(path_str)
    if m:
        year, lpscid = m.groups()
        doc_id = "lpsc%s-%s" % (year, lpscid)
        doc_url = "http://www.hou.usra.edu/meetings/lpsc20%s/pdf/%s.pdf" % (year, lpscid)
        year = (0 if len(year) > 3 else 2000 ) + int(year) # convert "15" to 2015
        return doc_id, year, doc_url
    return None, None


# KW: indexer.py isn't handling the 'sentences' field correctly;
# Solr ingestion fails.  I'm not sure we need it.  
# So for now, omitting it.
def map_basic(doc, noalter_prefix=["ner","rel"], nomap_prefix=["sentences"]):
    res = {}
    md = doc['metadata']
    res['id'] = doc['file']
    res['content'] = doc.get('content'),

    for src_key, src_val in md.items():
        # Skip over any fields we don't need in Solr
        if src_key in nomap_prefix:
            continue

        if src_key in md_map:
            for new_key in md_map[src_key]:
                res[new_key] = src_val
            continue

        # Update names of fields allow the schema to handle them
        # automatically (includes type info)
        new_key = src_key
        if not src_key in noalter_prefix:
            # is it multivalued?
            new_key = src_key.lower().replace(' ', '').strip()

            multivalued = type(src_val) == list

            new_key += "_t"  # treat them as strings by default
            if multivalued:
                new_key += "s"   # plural for multi valued
            new_key += "_md"
        res[new_key] = src_val

    parts = res['contentType'].split('/')
    res['mainType'] = parts[0]
    res['subType'] = parts[1]

    # TODO: detects int, float, date
    return [res]

def flatmap_journal(doc):
    """
    Maps schema of document and expands children documents into
    sub sequent documents
    """

    res = map_basic(doc)[0]
    for src, target in grobid_map.items():
        if src in res:
            res[target] = res[src]
            del res[src]

    # create a list of documents for Solr, starting with the document itself
    children = [res]
    # shorter Id instead of full path
    p_id, doc_year, doc_url = parse_lpsc_from_path(res['id'])
    print('Indexing %s from %s,\n  URL = %s' % (p_id, doc_year, doc_url))
    res['id'] = p_id
    res['type'] = 'doc'
    res['url'] = doc_url
    res['year'] = doc_year
    res['_path'] = '/'
    res['_depth'] = 0

    # add each NER annotation as a document for Solr
    if 'ner' in res:
        print('Indexing named entities.')
        names = res['ner']
        del res['ner']
        for i, name in enumerate(names):
            label = name['label'].lower()
            child = {
                'id': '%s_%s_%d_%d' % (p_id, label, 
                                       name['begin'], name['end']),
                'p_id': p_id,
                'name': name['text'],
                'can_name': canonical_target_name(name['text']) 
                if label == 'target' else canonical_name(name['text']),
                'type': label,
                'source': name.get('source', 'corenlp'),
                'span_start': name['begin'],
                'span_end': name['end'],
                '_path': '/%s' % label,
                '_depth': 1,
                }
            children.append(child)

    # add each JSRE relation annotation as a document for Solr
    if 'rel' in res:
        print('Indexing %d relations.' % len(res['rel']))
        rels = res['rel']
        del res['rel']
        for i, rel in enumerate(rels):
            label = rel['label'].lower()
            child = {
                'id': '%s_%s_%d' % (p_id, label, i),
                'p_id': p_id,
                'type': label,
                'source': rel.get('source', 'jsre'),
                'target_names_ss': rel['target_names'],
                'cont_names_ss':   rel['cont_names'],
                'cont_ids_ss': [p_id + '_' + id for id in rel['cont_ids']],
                'excerpt_t': rel['sentence'],
                '_path': '/%s' % label,
                '_depth': 1,
                }
            children.append(child)

    if res.get('title'):
        res['title'] = string.capwords(res.get('title', ''))
    else:
        res['title'] = 'Unknown'
    if res.get('authors'):
        res['primaryauthor'] = get_primary_author(res['authors'])
    else:
        res['authors'], res['primaryauthor'] = 'Unknown', 'Unknown'
    return children

def get_primary_author(au):
    '''
    gets the primary author name.
    Heuristic: first phrase in 'authors' consisting of words longer than 1 char
    '''
    auwords = au.split()
    pa = ''
    in_last_name = False
    for auw in auwords:
        if len(auw) > 1:
            if in_last_name:
                pa += (' ' + auw)
            else:
                pa = auw
                in_last_name = True
        else:
            if in_last_name:  # Done!
                break
    return string.capwords(pa)

schema_map = {
    'basic': map_basic,
    'journal': flatmap_journal
}

def index(solr, docs, n_docs):
    count, succeeded = solr.post_iterator(docs, commit=True, buffer_size=20)
    if succeeded:
        print("Indexed %d Solr docs from %d docs." % (count, n_docs))
    else:
        print("Error: Failed after %d docs. Please debug and start again" % count)


def main():
    # Step : Parse CLI args
    parser = ArgumentParser(description="This tool can read JSON line dump and index to solr.",
                            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                            version="1.0")

    parser.add_argument("-i", "--in", help="Path to Input JSON line file.", required=True)
    parser.add_argument("-s", "--solr-url", help="URL of Solr core.", default="http://localhost:8983/solr/docsdev")
    parser.add_argument("-sc", "--schema", help="Schema Mapping to be used. Options:\n%s" % schema_map.keys(),
                        default='journal')
    args = vars(parser.parse_args())
    if args['schema'] not in schema_map:
        print("Error: %s  schema is unknown. Known options: %s" % (args['schema'], schema_map.keys()))
        sys.exit(1)

    schema_mapper = schema_map[args['schema']]
    docs = read_jsonlines(args['in'])
    # map to schema
    docs = map(schema_mapper, docs)

    def merge_lists(docs):
        for docgroup in docs:
            for doc in docgroup:
                yield doc

    docs_solr = merge_lists(docs)

    # send to solr
    solr = Solr(args['solr_url'])
    index(solr, docs_solr, len(docs))

if __name__ == '__main__':
    main()
