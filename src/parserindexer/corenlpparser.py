from __future__ import print_function

from parser import *
from journalparser import *
from pycorenlp import StanfordCoreNLP
import itertools

class CoreNLPParser(JournalParser):
    CORENLP_PARSER = "edu.stanford.nlp.pipeline.CoreNLPServer"

    def __init__(self, **kwargs):
        super(CoreNLPParser, self).__init__(**kwargs)
        self.corenlp = StanfordCoreNLP(kwargs['corenlp_url'] )
        self.props = {
            'annotators': 'ner',
            'outputFormat': 'json',
            'ner.useSUTime': False,  # dont want SUTime model
            'ner.applyNumericClassifiers': False, # Dont want numeric classifier
        }
        if kwargs.get('ner_model'): # set NER model from CLI
            self.props['ner.model'] = kwargs['ner_model']
        print("CoreNLP Properties : ", self.props)

    def parse_names(self, text, meta):
        if type(text) != str:
            text = text.encode('ascii', errors='ignore')
        if text[0].isspace(): # dont strip white spaces
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
        new_names = []
        skip_names = []
        for n in names:
            if n in skip_names:
                continue
            next_name = [n2 for n2 in names if \
                         n['label'] == 'Target' and
                         n2['label'] == n['label'] and
                         int(n2['begin']) == int(n['end']) + 1 and
                         text[int(n['end'])] == ' ']
            if len(next_name) > 0:
                print('Merging %s and %s' % (n['text'], next_name[0]['text']))
                n['text'] += ' ' + next_name[0]['text']
                n['end']  = next_name[0]['end']
                skip_names.append(next_name[0])

            # Either way, save this one
            new_names.append(n)

        if len(names) != len(new_names):
            print('%d -> %d NERs' % (len(names), len(new_names)))

        if names:
            meta['ner'] = names
            meta['X-Parsed-By'].append(CoreNLPParser.CORENLP_PARSER)
        meta['sentences'] = output['sentences']
        return meta

if __name__ == '__main__':
    cli_p = CliParser(CoreNLPParser)
    cli_p.add_argument('-c', '--corenlp-url', help="CoreNLP Server URL", default="http://localhost:9000")
    cli_p.add_argument('-n', '--ner-model', help="Path (on Server side) to NER model ", required=False)
    args = vars(cli_p.parse_args())
    main(CoreNLPParser, args)
