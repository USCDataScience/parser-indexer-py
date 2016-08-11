#!/usr/bin/env python3
from __future__ import print_function
from pycorenlp import StanfordCoreNLP
import os
from argparse import ArgumentParser
import json
import itertools

class NerToBratConverter(object):
    def __init__(self, corenlp_url='http://localhost:9000'):
        '''
        Create Converter for converting NER annotations to Brat annotations
        classifier training data.

        To start the server checkout: http://stanfordnlp.github.io/CoreNLP/corenlp-server.html#getting-started
        '''
        self.corenlp = StanfordCoreNLP(corenlp_url)

    def convertToBrat(self, text_file, ann_file):
        print("Processing %s" % text_file)
        with open(text_file) as f:
            text = f.read()

        props = { 'annotators': 'tokenize,ssplit,pos,ner', 'outputFormat': 'json'}
        output = self.corenlp.annotate(text, properties=props)
        # flatten sentences and tokens
        tokenlists = [s['tokens'] for s in output['sentences']]
        tokens = itertools.chain.from_iterable(tokenlists)

        count = 1
        with open(ann_file, 'w', 1) as out:
            for token in tokens:
                if token['ner'] != 'O':
                    rec = "T%d\t%s %d %d\t%s" % (count,
                            token['ner'],
                            token['characterOffsetBegin'],
                            token['characterOffsetEnd'],
                            token['originalText'])
                    # print(rec)
                    out.write(rec)
                    out.write("\n")
                    count += 1
        print("Wrote %s" % ann_file)

    def convert_all(self, input_paths):
        with open(input_paths) as paths:
            for d in map(lambda x: x.split(','), map(lambda x: x.strip(), paths)):
                self.convertToBrat(d[0], d[1])

if __name__ == '__main__':

    parser = ArgumentParser(description="CoreNLP NER to Brat annotation converter")
    parser.add_argument("--in", help="""Input file, each line contains comma separated *.txt,*.ann\n
    To create the input file, follow these instructuions:
    $ ls $PWD/*.txt | sed -e 's/\(.*\)\.txt/\1.txt,\1.ann/g' > input.list""",
     required=True)
    args = vars(parser.parse_args())
    NerToBratConverter().convert_all(args['in'])
