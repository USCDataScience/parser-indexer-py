from __future__ import print_function

from parser import *
from corenlpparser import *
from jsreparser import JsreParser
import io, ntpath
from utils import canonical_name, canonical_target_name


class ParseAll(CoreNLPParser):

    def __init__(self, **kwargs):
        super(ParseAll, self).__init__(**kwargs)
        self.jsre_parser = JsreParser(**kwargs)
        self.jsre_model = kwargs['jsre_model']

        if not os.path.exists(self.jsre_model):
            print('Error: Could not find jSRE model %s.' % self.jsre_model)
            sys.exit(1)


    def generate_example_id(self, fnbase, index, ex_ind):
        # Create a unique identifier
        return '%s_%s_%s' % (fnbase, str(index), str(ex_ind))

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

    def generate_examples(self, targets, active, relations, examples, 
                          ex_ind, sentence, fnbase):
        for i in range(0, len(targets)):
            for j in range(0, len(active)):
                label = 0
                # Create a unique identifier
                id = self.generate_example_id(fnbase, sentence['index'], ex_ind)
                ex_ind += 1
                example = self.generate_example(id, label, sentence, 
                                                targets[i]['index'], 
                                                active[j]['index'])
                relations.append([targets[i], active[j], sentence])
                examples.append(example)
        return relations, examples, ex_ind


    def parse_file(self, path):
        parsed = super(ParseAll, self).parse_file(path)

        # Build jSRE examples
        (rel_target_element, jsre_ex_element) = ([], [])
        (rel_target_mineral, jsre_ex_mineral) = ([], [])
        (ex_ind_element, ex_ind_mineral) = (0, 0) 

        fn = ntpath.basename(path)
        fnbase = fn[:fn.find('.pdf')]
        print('%s: Parsing %d sentences.' % \
              (fn, len(parsed['metadata']['sentences'])))
        for s in parsed['metadata']['sentences']:
            # For each pair of target+(element|mineral) entities,
            # are they in a contains relationship?
            # Get the relevant entities (Target, Element, Mineral)
            targets = [t for t in s['tokens'] if t['ner'] == 'Target']
            minerals = [t for t in s['tokens'] if t['ner'] == 'Mineral']
            elements = [t for t in s['tokens'] if t['ner'] == 'Element']
            rel_target_element, jsre_ex_element, ex_ind_element = \
                    self.generate_examples(targets, elements, 
                                           rel_target_element,
                                           jsre_ex_element, 
                                           ex_ind_element,
                                           s, fnbase)
            rel_target_mineral, jsre_ex_mineral, ex_ind_mineral = \
                    self.generate_examples(targets, minerals, 
                                           rel_target_mineral,
                                           jsre_ex_mineral, 
                                           ex_ind_mineral,
                                           s, fnbase)

        total_rel = []
        for (jsre_fn, examples, relations) in \
            [('tmp_element', jsre_ex_element, rel_target_element),
             ('tmp_mineral', jsre_ex_mineral, rel_target_mineral)]:

            # Set up the jSRE example file
            with io.open(jsre_fn, 'w', encoding='utf8') as out:
                for example in examples:
                    out.write(example)
                out.close()

            # Call jSRE extraction (prediction)
            # This version works if you want to call separate
            # element, mineral models.
            #self.jsre_parser.predict(self.jsre_model + jsre_fn[4:] + '.model',
            # This version works if you want one merged model.
            self.jsre_parser.predict(self.jsre_model,
                                     jsre_fn, jsre_fn + '_out')

            rel = []
            # Read results from jSRE output files 
            with io.open(jsre_fn + '_out', 'r') as inf:
                lines = inf.readlines()
                n_cand = len(lines)
                for (l,ex) in zip(lines, relations):
                    # If the label is non-zero, then it's a relationship
                    # 0 - negative
                    # 1 - entity_1 contains entity_2
                    # 2 - entity_2 contains entity_1
                    label = float(l)
                    if label > 0.0:
                        #print('%f: target %s, component %s' % (label, 
                        #                                       ex[0]['word'], 
                        #                                       ex[1]['word']))
                        # To store in Solr:
                        cont = {
                            'label': 'contains',  # also stored as 'type'
                            # target_names (list), cont_names (list)
                            'target_names': [canonical_target_name(ex[0]['word'])],
                            'cont_names':   [canonical_name(ex[1]['word'])],
                            # target_ids (list), cont_ids (list) 
                            # - p_id prepended in indexer.py
                            'target_ids': ['%s_%d_%d' % (ex[0]['ner'].lower(),
                                    ex[0]['characterOffsetBegin'],
                                    ex[0]['characterOffsetEnd'])],
                            'cont_ids': ['%s_%d_%d' % (ex[1]['ner'].lower(),
                                    ex[1]['characterOffsetBegin'],
                                    ex[1]['characterOffsetEnd'])],
                            # excerpt_t (sentence)
                            'sentence': ' '.join([t['originalText'] for \
                                                  t in ex[2]['tokens']]),
                            # source: 'corenlp' (later, change to 'jsre')
                            'source': 'corenlp',
                        }
                        rel.append(cont)
            n_rel = len(rel)
            print('  Extracted %d target-%s relations, from %d candidates.' % \
                  (n_rel, 
                   jsre_fn[4:],
                   n_cand))
            total_rel += rel

            # Remove tmp files
            os.remove(jsre_fn)
            os.remove(jsre_fn + '_out')
                    
        if total_rel:
            parsed['metadata']['rel'] = total_rel

        sys.stdout.flush()

        # Return parsed
        parsed['metadata']['X-Parsed-By'].append(JsreParser.JSRE_PARSER)
        return parsed


if __name__ == '__main__':
    cli_p = CliParser(ParseAll)
    cli_p.add_argument('-c', '--corenlp-url', help="CoreNLP Server URL", default="http://localhost:9000")
    cli_p.add_argument('-n', '--ner-model', help="Path (on Server side) to NER model ", required=False)
    cli_p.add_argument("-j", "--jsre", help="Path to jSRE installation directory.", required=True)
    cli_p.add_argument("-m", "--jsre-model", help="Base path to jSRE models.", required=True)
    args = vars(cli_p.parse_args())
    main(ParseAll, args)
