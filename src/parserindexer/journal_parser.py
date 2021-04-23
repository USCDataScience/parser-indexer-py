from __future__ import print_function

import re
import sys
import json
from parser import Parser
from ioutils import read_lines
from tika_parser import TikaParser
from jsre_parser import JsreParser
from brat_ann_indexer import extract_references


class JournalParser(Parser):
    """ The JournalParser removes special text/format for journal articles """
    PDF_TYPE = "application/pdf"

    def __init__(self):
        super(JournalParser, self).__init__('journal_parser')

    def parse(self, text, metadata):
        if type(metadata['Content-Type']) == list:
            assert JournalParser.PDF_TYPE in metadata['Content-Type']
        else:
            assert metadata['Content-Type'] == JournalParser.PDF_TYPE

        assert type(text) == str or type(text) == unicode

        # 1. Translate some UTF-8 punctuation to ASCII
        punc = {
            # single quote
            0x2018: 0x27, 0x2019: 0x27,
            # double quote
            0x201C: 0x22, 0x201D: 0x22,
            # hyphens
            0x2010: 0x2d, 0x2011: 0x2d, 0x2012: 0x2d, 0x2013: 0x2d,
            # comma
            0xFF0C: 0x2c,
            # space
            0x00A0: 0x20,
            # bullets
            0x2219: 0x2e, 0x2022: 0x2e,
        }
        text = text.translate(punc)

        # 2. Replace newlines that separate words with a space (unless hyphen)
        text = re.sub(r'([^\s-])[\r|\n]+([^\s])', '\\1 \\2', text)

        # 3. Remove hyphenation at the end of lines
        # (this is sometimes bad, as with "Fe-\nrich")
        text = text.replace('-\n', '\n')

        # 4. Remove all newlines
        text = re.sub(r'[\r|\n]+', '', text)

        # 5. Move references to their own field (references)
        refs = extract_references(text)
        for ref_id in refs:  # preserve length; insert whitespace
            text = text.replace(refs[ref_id], ' ' * len(refs[ref_id]))

        return {
            'references': refs.values(),
            'cleaned_content': text
        }


def process(in_file, in_list, out_file, tika_server_url, corenlp_server_url,
            ner_model, jsre_root, jsre_model, jsre_tmp_dir):
    if in_file and in_list:
        print('[ERROR] in_file and in_list cannot be provided simultaneously')
        sys.exit(1)

    tika_parser = TikaParser(tika_server_url)
    journal_parser = JournalParser()
    jsre_parser = JsreParser(corenlp_server_url, ner_model, jsre_root,
                             jsre_model, jsre_tmp_dir)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in files:
        tika_dict = tika_parser.parser(f)
        journal_dict = journal_parser.parse(tika_dict['content'],
                                            tika_dict['metadata'])
        jsre_dict = jsre_parser.parse(journal_dict['cleaned_content'])

        tika_dict['content_ann_s'] = journal_dict['cleaned_content']
        tika_dict['references'] = journal_dict['references']
        tika_dict['metadata']['ner'] = jsre_dict['ner']
        tika_dict['metadata']['rel'] = jsre_dict['relation']
        tika_dict['metadata']['sentences'] = jsre_dict['sentences']
        tika_dict['metadata']['X-Parsed-By'] = jsre_dict['X-Parsed-By']

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
