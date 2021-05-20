from __future__ import print_function

import os
import sys
import json
import warnings
import itertools
import subprocess
from utils import canonical_name
from utils import canonical_target_name
from tika_parser import TikaParser
from corenlp_parser import CoreNLPParser
from ioutils import read_lines


class JsreParser(CoreNLPParser):
    """ Relation extraction using JSRE package. The JsreParser class depends on
    the outputs provided by the CoreNLPParser class.
    """
    JSRE_PARSER = "org.itc.irst.tcc.sre.Predict"

    def __init__(self, corenlp_server_url, ner_model, jsre_root, jsre_model,
                 jsre_tmp_dir='/tmp'):
        super(JsreParser, self).__init__(corenlp_server_url, ner_model,
                                         'jsre_parser')

        self.jsre_root = jsre_root
        self.jsre_model = jsre_model
        self.jsre_tmp_dir = jsre_tmp_dir
        self.set_classpath()

    def set_classpath(self):
        jars = [
            os.path.join(self.jsre_root, 'dist/xjsre.jar'),
            os.path.join(self.jsre_root, 'lib/commons-beanutils.jar'),
            os.path.join(self.jsre_root, 'lib/commons-cli-1.0.jar'),
            os.path.join(self.jsre_root, 'lib/commons-collections.jar'),
            os.path.join(self.jsre_root, 'lib/commons-digester.jar'),
            os.path.join(self.jsre_root, 'lib/commons-logging.jar'),
            os.path.join(self.jsre_root, 'lib/libsvm-2.8.jar'),
            os.path.join(self.jsre_root, 'lib/log4j-1.2.8.jar')
        ]

        for jar in jars:
            if not os.path.exists(jar):
                raise RuntimeError('JSRE required JAR file not found: %s' %
                                   os.path.abspath(jar))

        os.environ['CLASSPATH'] = ':'.join(jars)

    @staticmethod
    def prepare_jsre_input(targets, components, sentence,
                           rel_id):
        relations = list()
        records = list()

        tc_combinations = itertools.product(targets, components)
        for idx, (target, component) in enumerate(tc_combinations):
            record_id = '%s_%d_%d' % (rel_id, sentence['index'], idx)
            body = ''

            for token in sentence['tokens']:
                if token['index'] == target['index']:
                    entity_label = 'A'
                elif token['index'] == component['index']:
                    entity_label = 'T'
                else:
                    entity_label = 'O'

                body += '%d&&%s&&%s&&%s&&%s&&%s ' % (
                    token['index'] - 1, token['word'], token['lemma'],
                    token['pos'], token['ner'], entity_label)

            records.append('%d\t%s\t%s\n' % (0, record_id, body))
            relations.append([target, component, sentence])

        return relations, records

    def predict(self, in_file, out_file):
        cmd = ['java', '-mx256M', self.JSRE_PARSER, in_file,
               self.jsre_model, out_file]

        fnull = open(os.devnull, 'w')
        subprocess.call(cmd, stdout=fnull, stderr=subprocess.STDOUT)
        fnull.close()

    def parse(self, text):
        corenlp_dict = super(JsreParser, self).parse(text)

        relations = list()
        records = list()
        for sentence in corenlp_dict['sentences']:
            targets = [t for t in sentence['tokens'] if t['ner'] == 'Target']
            elements = [t for t in sentence['tokens'] if t['ner'] == 'Element']
            minerals = [t for t in sentence['tokens'] if t['ner'] == 'Mineral']

            rels, recs = JsreParser.prepare_jsre_input(targets, elements,
                                                       sentence, rel_id='te')
            relations.extend(rels)
            records.extend(recs)

            rels, recs = JsreParser.prepare_jsre_input(targets, minerals,
                                                       sentence, rel_id='tm')
            relations.extend(rels)
            records.extend(recs)

        contains_relation = list()
        in_file = '%s/jsre_input.txt' % self.jsre_tmp_dir
        out_file = '%s/jsre_output.txt' % self.jsre_tmp_dir

        with open(in_file, 'w', encoding='utf8') as f:
            for r in records:
                f.write(r)

        self.predict(in_file, out_file)
        if not os.path.exists(out_file):
            warnings.warn('jSRE output file not found, which indicates jSRE '
                          'run may be failed.')

            return contains_relation

        jsre_out_file = open(out_file, 'r')
        labels = jsre_out_file.readlines()
        for label, rel in zip(labels, relations):
            # If the label is non-zero, then it's a relationship
            # 0 - negative
            # 1 - entity_1 contains entity_2
            # 2 - entity_2 contains entity_1
            if label == '0':
                continue

            contains_relation.append({
                'label': 'contains',
                'target_names': [canonical_target_name(rel[0]['word'])],
                'cont_names': [canonical_name(rel[1]['word'])],
                'target_ids': ['%s_%d_%d' % (rel[0]['ner'].lower(),
                                             rel[0]['characterOffsetBegin'],
                                             rel[0]['characterOffsetEnd'])],
                'cont_ids': ['%s_%d_%d' % (rel[1]['ner'].lower(),
                                           rel[1]['characterOffsetBegin'],
                                           rel[1]['characterOffsetEnd'])],
                'sentence':  ' '.join([t['originalText']
                                       for t in rel[2]['tokens']]),
                'source': 'jsre'
            })

        jsre_out_file.close()
        os.remove(in_file)
        os.remove(out_file)

        return {
            'ner': corenlp_dict['ner'],
            'sentences': corenlp_dict['sentences'],
            'relation': contains_relation,
            'X-Parsed-By': JsreParser.JSRE_PARSER
        }


def process(in_file, in_list, out_file, tika_server_url, corenlp_server_url,
            ner_model, jsre_root, jsre_model, jsre_tmp_dir):
    if in_file and in_list:
        print('[ERROR] in_file and in_list cannot be provided simultaneously')
        sys.exit(1)

    tika_parser = TikaParser(tika_server_url)
    jsre_parser = JsreParser(corenlp_server_url, ner_model, jsre_root,
                             jsre_model, jsre_tmp_dir)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in files:
        tika_dict = tika_parser.parse(f)
        jsre_dict = jsre_parser.parse(tika_dict['content'])

        tika_dict['metadata']['ner'] = jsre_dict['ner']
        tika_dict['metadata']['rel'] = jsre_dict['relation']
        tika_dict['metadata']['sentences'] = jsre_dict['sentences']
        tika_dict['metadata']['X-Parsed-By'].append(jsre_dict['X-Parsed-By'])

        out_f.write(json.dumps(tika_dict))
        out_f.write('\n')

    out_f.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    input_parser = parser.add_mutually_exclusive_group(required=True)

    input_parser.add_argument('-i', '--in_file', help='Path to input file')
    input_parser.add_argument('-li', '--in_list', help='Path to input list')
    parser.add_argument('-o', '--out_file', required=True,
                        help='Path to output JSON file')
    parser.add_argument('-p', '--tika_server_url', required=False,
                        help='Tika server URL')
    parser.add_argument('-c', '--corenlp_server_url',
                        default='http://localhost:9000',
                        help='CoreNLP Server URL')
    parser.add_argument('-n', '--ner_model', required=False,
                        help='Path to a Named Entity Recognition (NER) model')
    parser.add_argument('-jr', '--jsre_root', default='/proj/mte/jSRE/jsre-1.1',
                        help='Path to jSRE installation directory. Default is '
                             '/proj/mte/jSRE/jsre-1.1')
    parser.add_argument('-jm', '--jsre_model', required=True,
                        help='Path to jSRE model')
    parser.add_argument('-jt', '--jsre_tmp_dir', default='/tmp',
                        help='Path to a directory for jSRE to temporarily '
                             'store input and output files. Default is /tmp')
    args = parser.parse_args()
    process(**vars(args))
