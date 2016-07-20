from __future__ import print_function
from argparse import ArgumentParser
from ioutils import read_jsonlines
from solr import Solr
import sys


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
    # TODO: update this
}
# journals map
grobid_map = {
    'grobid:header_title_ts_md': 'title',
    'dcterms:created_ts_md': 'createdAt',
    'mdcterms:modified_ts_md': 'modifiedAt'
}


def map_basic(doc):
    res = {}
    md = doc['metadata']
    res['id'] = doc['file']
    res['content'] = doc.get('content'),

    for src_key, src_val in md.items():
        if src_key in md_map:
            for new_key in md_map[src_key]:
                res[new_key] = src_val
            continue

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
