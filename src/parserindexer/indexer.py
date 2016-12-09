from __future__ import print_function
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
    p_id = '/'.join(res['id'].split("/")[-2:])
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
                'id': '%s_%d' % (p_id, i),
                'name': name['text'],
                'type': label,
                'span_start': name['begin'],
                'span_end': name['end'],
                '_path': '/%s' % label,
                '_depth': 1,
                }
            children.append(child)
    if children:
        res['_childDocuments_'] = children
    res['title'] = string.capwords(res.get('title', ''))
    return res

schema_map = {
    'basic': map_basic,
    'journal': map_journal
}


def index():
    # Step : Parse CLI args
    parser = ArgumentParser(description="This tool can read JSON line dump and index to solr.",
                            version="1.0")

    parser.add_argument("-i", "--in", help="Path to Input JSON line file.", required=True)
    parser.add_argument("-s", "--solr-url", help="URL of Solr core.", required=True)
    parser.add_argument("-sc", "--schema", help="Schema Mapping to be used. Options:\n%s" % schema_map.keys(),
                        required=True)
    args = vars(parser.parse_args())
    if args['schema'] not in schema_map:
        print("Error: %s  schema is unknown. Known options: %s" % (args['schema'], schema_map.keys()))
        sys.exit(1)
    schema_mapper = schema_map[args['schema']]
    docs = read_jsonlines(args['in'])

    # map to schema
    docs = map(lambda doc: schema_mapper(doc), docs)

    # send to solr
    solr = Solr(args['solr_url'])
    count, succeeded = solr.post_iterator(docs, commit=True, buffer_size=20)
    if succeeded:
        print("Indexed %d docs." % count)
    else:
        print("Error: Failed after %d docs. Please debug and start again" % count)

if __name__ == '__main__':
    index()
