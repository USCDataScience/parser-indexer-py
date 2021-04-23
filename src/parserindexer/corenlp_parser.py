from __future__ import print_function

import os
import sys
import json
import itertools
from parser import Parser
from ioutils import read_lines
from tika_parser import TikaParser
from pycorenlp import StanfordCoreNLP

# The following two lines make CoreNLP happy
reload(sys)
sys.setdefaultencoding('UTF8')


class CoreNLPParser(Parser):
    """ The CoreNLPParser class builds upon Stanford CoreNLP package """
    def __init__(self, corenlp_server_url, ner_model,
                 parser_name='corenlp_parser'):
        super(CoreNLPParser, self).__init__(parser_name)

        self.corenlp = StanfordCoreNLP(corenlp_server_url)
        self.props = {
            'annotators': 'tokenize,ssplit,lemma,pos,ner',
            'outputFormat': 'json',
            # dont want SUTime model
            'ner.useSUTime': False,
            # Dont want numeric classifier
            'ner.applyNumericClassifiers': False,
        }
        if ner_model:
            if not os.path.exists(ner_model):
                raise RuntimeError('NER model not found: %s' %
                                   os.path.abspath(ner_model))
            self.props['ner.model'] = ner_model

    def parse(self, text):
        """ Named entity recognition (NER) using stanford CoreNLP package

        Args:
            text (str): A string (can be a long string) in which Named Entity
                Recognition will run.
        Return:
            this function returns a dictionary contains the NERs identified,
            sentences extracted, and name of the source parser
        """
        if type(text) != str:
            text = text.encode('utf8')
        if text[0].isspace():  # dont strip white spaces
            text = '.' + text[1:]

        output = self.corenlp.annotate(text, properties=self.props)

        # flatten sentences and tokens
        tokenlists = [s['tokens'] for s in output['sentences']]
        tokens = itertools.chain.from_iterable(tokenlists)
        names = []
        for token in tokens:
            if token['ner'] != 'O':
                name = {
                    'label': token['ner'],
                    'begin': token['characterOffsetBegin'],
                    'end': token['characterOffsetEnd'],
                    'text': token['originalText'],
                    'source': 'corenlp'
                }
                names.append(name)

        # Handle multi-word tokens:
        # Merge any adjacent Target tokens, if of the same type and
        # separated by a space, into one span.
        names.sort(key=lambda x: int(x['begin']))
        new_names = []
        skip_names = []
        for n in names:
            if n in skip_names:
                continue
            next_name = [n2 for n2 in names if
                         n['label'] == 'Target' and
                         n2['label'] == 'Target' and
                         int(n2['begin']) == int(n['end']) + 1]
            if len(next_name) > 0:
                n['text'] += ' ' + next_name[0]['text']
                n['end'] = next_name[0]['end']
                skip_names.append(next_name[0])

            # Either way, save this one
            new_names.append(n)

        return {
            'ner': new_names,
            'X-Parsed-by': CoreNLPParser.CORENLP_PARSER,
            'sentences': output['sentences']
        }


def process(in_file, in_list, out_file, tika_server_url, corenlp_server_url,
            ner_model):
    if in_file and in_list:
        print('[ERROR] in_file and in_list cannot be provided simultaneously')
        sys.exit(1)

    tika_parser = TikaParser(tika_server_url)
    corenlp_parser = CoreNLPParser(corenlp_server_url, ner_model)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in files:
        tika_dict = tika_parser.parse(f)
        corenlp_dict = corenlp_parser.parse(tika_dict['content'])

        tika_dict['metadata']['ner'] = corenlp_dict['ner']
        tika_dict['metadata']['X-Parsed-By'] = corenlp_dict['X-Parsed-By']
        tika_dict['metadata']['sentences'] = corenlp_dict['sentences']

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
                        default='"http://localhost:9000',
                        help='CoreNLP Server URL')
    parser.add_argument('-n', '--ner_model', required=False,
                        help='Path to a Named Entity Recognition (NER) model ')
    args = parser.parse_args()
    process(**vars(args))
