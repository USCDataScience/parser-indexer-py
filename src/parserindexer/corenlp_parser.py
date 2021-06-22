from __future__ import print_function

import os
import sys
import json
import urllib
import itertools
from tqdm import tqdm
from parser import Parser
from ioutils import read_lines
from ads_parser import AdsParser
from pycorenlp import StanfordCoreNLP

# The following two lines make CoreNLP happy
reload(sys)
sys.setdefaultencoding('UTF8')


class CoreNLPParser(Parser):
    """ The CoreNLPParser class builds upon Stanford CoreNLP package """

    CORENLP_PARSER = "edu.stanford.nlp.pipeline.CoreNLPServer"

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
            'timeout': '60000',
            # Don't need fine grained recognition with corenlp built-in NER
            # models
            'ner.applyFineGrained': False
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

        # Quote (with percent-encoding) reserved characters in URL for CoreNLP
        text = urllib.quote(text)
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
            'X-Parsed-By': CoreNLPParser.CORENLP_PARSER,
            'sentences': output['sentences']
        }


def process(in_file, in_list, out_file, tika_server_url, corenlp_server_url,
            ner_model, ads_url, ads_token):
    if in_file and in_list:
        print('[ERROR] in_file and in_list cannot be provided simultaneously')
        sys.exit(1)

    ads_parser = AdsParser(ads_token, ads_url, tika_server_url)
    corenlp_parser = CoreNLPParser(corenlp_server_url, ner_model)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in tqdm(files):
        ads_dict = ads_parser.parse(f)
        corenlp_dict = corenlp_parser.parse(ads_dict['content'])

        ads_dict['metadata']['ner'] = corenlp_dict['ner']
        ads_dict['metadata']['X-Parsed-By'].append(corenlp_dict['X-Parsed-By'])
        ads_dict['metadata']['sentences'] = corenlp_dict['sentences']

        out_f.write(json.dumps(ads_dict))
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
                        help='Path to a Named Entity Recognition (NER) model ')
    parser.add_argument('-a', '--ads_url',
                        default='https://api.adsabs.harvard.edu/v1/search/query',
                        help='ADS RESTful API. The ADS RESTful API should not '
                             'need to be changed frequently unless someting at '
                             'the ADS is changed.')
    parser.add_argument('-t', '--ads_token',
                        default='jON4eu4X43ENUI5ugKYc6GZtoywF376KkKXWzV8U',
                        help='The ADS token, which is required to use the ADS '
                             'RESTful API. The token was obtained using the '
                             'instructions at '
                             'https://github.com/adsabs/adsabs-dev-api#access. '
                             'The ADS token should not need to be changed '
                             'frequently unless something at the ADS is '
                             'changed.')

    args = parser.parse_args()
    process(**vars(args))
