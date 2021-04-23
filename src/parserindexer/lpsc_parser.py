from __future__ import print_function

import re
import sys
import json
from parser import Parser
from ioutils import read_lines
from tika_parser import TikaParser
from jsre_parser import JsreParser
from brat_ann_indexer import extract_references


class LpscParser(Parser):
    """ This class a specialized parser for parsing Journals which are in PDF
    format
    """
    JOURNAL_PARSER = 'org.apache.tika.parser.journal.JournalParser'
    PDF_TYPE = "application/pdf"

    def __init__(self):
        super(LpscParser, self).__init__('lpsc_parser')

    def parse(self, text, metadata):
        if type(metadata['Content-Type']) == list:
            assert LpscParser.PDF_TYPE in metadata['Content-Type']
        else:
            assert metadata['Content-Type'] == LpscParser.PDF_TYPE

        # Improve parsing and save in parsed['content_ann_s']
        assert type(text) == str or type(text) == unicode

        # New parsing (after extract_text_utf8.py)
        # 0. Translate some UTF-8 punctuation to ASCII
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

        # 1. Replace newlines that separate words with a space (unless hyphen)
        text = re.sub(r'([^\s-])[\r|\n]+([^\s])', '\\1 \\2', text)

        # 2. Remove hyphenation at the end of lines
        # (this is sometimes bad, as with "Fe-\nrich")
        text = text.replace('-\n', '\n')

        # 3. Remove all newlines
        text = re.sub(r'[\r|\n]+', '', text)

        # 4. Remove xxxx.PDF
        text = re.sub(r'([0-9][0-9][0-9][0-9].PDF)', '', text,
                      flags=re.IGNORECASE)
        # And "xx(th|st) Lunar and Planetary Science Conference ((19|20)xx)"
        text = re.sub(r'([0-9][0-9].. Lunar and Planetary Science Conference '
                      r'\((19|20)[0-9][0-9]\)) ?', '', text,
                      flags=re.IGNORECASE)
        # And "Lunar and Planetary Science XXXIII (2002)"
        # with Roman numeral and optional year
        text = re.sub(r'(Lunar and Planetary Science '
                      r'[CDILVXM]+( \((19|20)[0-9][0-9]\))?) ?', '', text,
                      flags=re.IGNORECASE)

        # 5. Remove mailto: links
        text = re.sub(r'mailto:[^\s]+', '', text)

        # 6. Move references to their own field (references)
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
    lpsc_parser = LpscParser()
    jsre_parser = JsreParser(corenlp_server_url, ner_model, jsre_root,
                             jsre_model, jsre_tmp_dir)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in files:
        tika_dict = tika_parser.parser(f)
        lpsc_dict = lpsc_parser.parse(tika_dict['content'],
                                      tika_dict['metadata'])
        jsre_dict = jsre_parser.parse(lpsc_dict['cleaned_content'])

        tika_dict['content_ann_s'] = lpsc_dict['cleaned_content']
        tika_dict['references'] = lpsc_dict['references']
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
