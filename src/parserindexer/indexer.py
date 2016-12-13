from __future__ import print_function
import argparse
from argparse import ArgumentParser
from ioutils import read_jsonlines
from solr import Solr
import sys
import string


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


def map_basic(doc, noalter_prefix="ner"):
    res = {}
    md = doc['metadata']
    res['id'] = doc['file']
    res['content'] = doc.get('content'),

    for src_key, src_val in md.items():
        if src_key in md_map:
            for new_key in md_map[src_key]:
                res[new_key] = src_val
            continue

        new_key = src_key
        if not src_key.startswith(noalter_prefix):
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
    return res


def map_journal(doc):
    res = map_basic(doc)
    for src, target in grobid_map.items():
        if src in res:
            res[target] = res[src]
            del res[src]

    # nested documents in solr
    children = []
    # shorter Id instead of full path
    p_id = res['id'].split("/")[-1].replace(".pdf", '')
    res['id'] = p_id
    res['type'] = 'doc'
    res['_path'] = '/'
    res['_depth'] = 0
    if 'ner' in res:
        names = res['ner']
        del res['ner']
        for i, name in enumerate(names):
            label = name['label'].lower()
            child = {
                'id': '%s_%s_%d' % (p_id, label, i),
                'name': name['text'],
                'type': label,
                'source': name.get('source', 'corenlp'),
                'span_start': name['begin'],
                'span_end': name['end'],
                '_path': '/%s' % label,
                '_depth': 1,
                }
            children.append(child)
    if children:
        res['_childDocuments_'] = children
    if res.get('title'):
        res['title'] = string.capwords(res.get('title', ''))
    else:
        res['title'] = 'Unknown'
    if res.get('authors'):
        res['primaryauthor'] = get_primary_author(res['authors'])
    else:
        res['authors'], res['primaryauthor'] = 'Unknown', 'Unknown'
    return res



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
    'journal': map_journal
}

def index(solr, docs, update):
    if update:
        print("Updating documents")
        def update_doc(new_doc):
            # NOTE: solr doesnt perform atomic updates on nested documents
            #       So, we prepare the updated document at the client side and then reindex it
            #       https://issues.apache.org/jira/browse/SOLR-6596
            old_doc = solr.get(new_doc['id'], fl="*,[child parentFilter=type:doc limit=10000]")
            if old_doc:
                if '_childDocuments_' in old_doc:
                    if not '_childDocuments_' in new_doc:
                        new_doc['_childDocuments_'] = []
                    new_doc['_childDocuments_'].extend(old_doc['_childDocuments_'])
                if 'content_ann_s' in old_doc:
                    new_doc['content_ann_s'] = old_doc['content_ann_s']
            else:
                print("WARN: Doc doesnt exists in index so no update performed for %s" % new_doc['id'])
            return new_doc
        docs = map(update_doc, docs)

    count, succeeded = solr.post_iterator(docs, commit=True, buffer_size=20)
    if succeeded:
        print("Indexed %d docs." % count)
    else:
        print("Error: Failed after %d docs. Please debug and start again" % count)


def main():
    # Step : Parse CLI args
    parser = ArgumentParser(description="This tool can read JSON line dump and index to solr.",
                            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                            version="1.0")

    parser.add_argument("-i", "--in", help="Path to Input JSON line file.", required=True)
    parser.add_argument("-s", "--solr-url", help="URL of Solr core.", default="http://localhost:8983/solr/docs")
    parser.add_argument("-sc", "--schema", help="Schema Mapping to be used. Options:\n%s" % schema_map.keys(),
                        default='journal')
    parser.add_argument("-u", "--update", action="store_true", help="Update documents in the index", default=False)
    args = vars(parser.parse_args())
    if args['schema'] not in schema_map:
        print("Error: %s  schema is unknown. Known options: %s" % (args['schema'], schema_map.keys()))
        sys.exit(1)

    schema_mapper = schema_map[args['schema']]
    docs = read_jsonlines(args['in'])
    # map to schema
    docs = map(schema_mapper, docs)
    # send to solr
    solr = Solr(args['solr_url'])
    index(solr, docs, args['update'])


if __name__ == '__main__':
    main()
