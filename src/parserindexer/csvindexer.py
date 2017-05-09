
import csv
import argparse
from solr import Solr
import ast
import re
import uuid
import json
import codecs

class CSVIndexer():
    '''
    This tool indexes a CSV file into SOLR
    '''

    # this is a basic field mappings
    suffix = {
        int: '_l',
        float:  '_d',
        str : '_t',
        bool: '_b'
    }

    known_fields = set(['id', 'type', 'url', 'name'])

    def read_docs(self, csv_file, _id_field=None, _type=None):
        '''Reads the records in a CSV file'''
        with codecs.open(csv_file, 'r', 'UTF-8', errors='ignore') as csvp:
            reader = csv.DictReader(csvp)
            for row in reader:
                if _id_field: # id field specified
                    _id = row[_id_field]
                elif 'id' in row: # default id field exists
                    _id = row['id']
                else: # auto generate
                    _id = str(uuid.uuid4())
                rec = self.transform_schema(row, _id, _type)
                #print(json.dumps(rec, indent=1))
                yield rec

    def transform_schema(self, doc, _id=None, _type=None):
        '''Transforms key names to match with solr schema'''
        res = {}
        for k, v in doc.items():
            if v is None or v.strip() == '' or v.lower() == 'null':
                continue
            if re.match(pattern='^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$', string=v):
                v = ast.literal_eval(v)
            k = k.lower().strip().replace(' ', '_')
            if k not in CSVIndexer.known_fields: # transform
                if type(v) == tuple:
                    v = list(v)
                    k += CSVIndexer.suffix[type(v[0])]
                    k += "s" # plural
                else:
                    k += CSVIndexer.suffix[type(v)]
            res[k] = v
        if _id:
            res['id'] = _id
        if _type:
            res['type'] = _type
        return res

    def index(self, docs, solr_url):
        solr = Solr(solr_url)
        success, count = solr.post_iterator(docs)
        if success:
            print("Indexed %d docs" % count)
        else:
            print("Error: Indexing failed, check solr logs")

def main():
    ap = argparse.ArgumentParser(
    description="This tool can index CSV files to solr.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter, version="1.0")
    ap.add_argument('-i', '--in', help="Path to input csv file", required=True)
    ap.add_argument('-s', '--solr-url', help="Solr URL", default="http://localhost:8983/solr/docsdev")
    ap.add_argument('-t', '--type', help="document type", required=True)
    ap.add_argument('-if', '--id-field', help="ID field")
    args = vars(ap.parse_args())
    csvi = CSVIndexer()
    docs = csvi.read_docs(args['in'], args['id_field'], args['type'])
    csvi.index(docs, args['solr_url'])

if __name__ == '__main__':
    main()
