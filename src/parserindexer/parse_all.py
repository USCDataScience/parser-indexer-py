from __future__ import print_function

from parser import *
from corenlpparser import *
from jsreparser import JsreParser
import io, ntpath


class ParseAll(CoreNLPParser):

    def __init__(self, **kwargs):
        super(ParseAll, self).__init__(**kwargs)
        self.jsre_parser = JsreParser(**kwargs)

    def generate_example_id(self, fnbase, index, ex_id):
        # Create a unique identifier
        return '%s_%s_%s' % (fnbase, str(index), str(ex_id))

    def generate_example(self, id, label, sentence, target_index, active_index):
        body = ''
        for t in sentence['tokens']:
            # Target entity is the agent;
            # Element entity is the target (of the relation)
            if t['index'] == target_index:
                entity_label = 'A'
            elif t['index'] == active_index:
                entity_label = 'T'
            else:
                entity_label = 'O'

            # CoreNLP indexes starting at 1
            body += '%d&&%s&&%s&&%s&&%s&&%s ' % (t['index'] - 1,
                                                 t['word'],
                                                 t['lemma'],
                                                 t['pos'],
                                                 t['ner'],
                                                 entity_label)
        # Output the example
        example = '%s\t%s\t%s\n' % (label, id, body)
        return example

    def generate_examples(self, targets, active, relations, examples, ex_id, sentence, fnbase):
        for i in range(0, len(targets)):
            for j in range(0, len(active)):
                label = 0
                # Create a unique identifier
                id = self.generate_example_id(fnbase, sentence['index'], ex_id)
                ex_id += 1
                example = self.generate_example(id, label, sentence, targets[i]['index'], active[j]['index'])
                relations.append([targets[i], active[j], sentence])
                examples.append(example)
        return relations, examples, ex_id

    def parse_file(self, path):
        parsed = super(ParseAll, self).parse_file(path)
        # Build jSRE example - creates tmp_mineral and tmp_element file
        target_mineral = []
        example_mineral = []
        target_element = []
        example_element = []
        fn = ntpath.basename(path)
        fnbase = fn[:fn.find('.pdf')]
        ex_mineral_id = 0
        ex_element_id = 0
        print('Parsing %d sentences.' % len(parsed['metadata']['sentences']))
        for s in parsed['metadata']['sentences']:
            # For each pair of target+(element|mineral) entities,
            # are they in a contains relationship?
            # Get the relevant entities (Target, Element, Mineral)
            targets = [t for t in s['tokens'] if t['ner'] == 'Target']
            minerals = [t for t in s['tokens'] if t['ner'] == 'Mineral']
            elements = [t for t in s['tokens'] if t['ner'] == 'Element']
            target_mineral, example_mineral, ex_mineral_id = \
                    self.generate_examples(targets, minerals, target_mineral,
                                           example_mineral, ex_mineral_id,
                                           s, fnbase)
            target_element, example_element, ex_element_id = \
                    self.generate_examples(targets, elements, target_element,
                                           example_element, ex_element_id,
                                           s, fnbase)
        #with io.open('tmp_mineral', 'w', encoding='utf8') as out:
        #    for example in example_mineral:
        #        out.write(example)
        with io.open('tmp_element', 'w', encoding='utf8') as out:
            for example in example_element:
                out.write(example)
            out.close()

        # Call jSRE extraction
        #self.jsre_parser.predict('tmp_mineral', 'tmp_mineral_out')
        self.jsre_parser.predict('tmp_element', 'tmp_element_out')

        # TODO: Read results from jSRE output files 
        rel = []
        with io.open('tmp_element_out', 'r') as inf:
            lines = inf.readlines()
            for (l,ex) in zip(lines, target_element):
                # If the label is non-zero, then it's a relationship
                # 0 - negative
                # 1 - entity_1 contains entity_2
                # 2 - entity_2 contains entity_1
                label = float(l)
                if label > 0.0:
                    print('%f: target %s, element %s' % (label, 
                                                         ex[0]['word'], 
                                                         ex[1]['word']))
                    # To store in Solr:
                    cont = {
                        'label': 'contains',  # also stored as 'type'
                        # target_names_ss (list), cont_names_ss (list)
                        'target_names': [ex[0]['word']],
                        'cont_names':   [ex[1]['word']],
                        # excerpt_t (sentence)
                        'sentence': ' '.join([t['originalText'] for t in ex[2]['tokens']]),
                        # source: 'corenlp' (later, change to 'jsre')
                        'source': 'corenlp',
                    }
                    rel.append(cont)

                    
        print('-----------------')
        if rel:
            print('Adding relations.')
            parsed['metadata']['rel'] = rel

        # Remove tmp files
        #os.remove('tmp_mineral')
        #os.remove('tmp_mineral_out')
        os.remove('tmp_element')
        os.remove('tmp_element_out')

        # Return parsed
        parsed['metadata']['X-Parsed-By'].append(JsreParser.JSRE_PARSER)
        return parsed


if __name__ == '__main__':
    cli_p = CliParser(ParseAll)
    cli_p.add_argument('-c', '--corenlp-url', help="CoreNLP Server URL", default="http://localhost:9000")
    cli_p.add_argument('-n', '--ner-model', help="Path (on Server side) to NER model ", required=False)
    cli_p.add_argument("-j", "--jsre", help="Path to jSRE installation directory.", required=True)
    cli_p.add_argument("-m", "--jsre-model", help="Path to jSRE model.", required=True)
    args = vars(cli_p.parse_args())
    main(ParseAll, args)
