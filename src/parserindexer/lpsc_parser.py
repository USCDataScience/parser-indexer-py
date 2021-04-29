from __future__ import print_function

import re
import sys
import json
from ioutils import read_lines
from paper_parser import PaperParser
from tika_parser import TikaParser
from jsre_parser import JsreParser


class LpscParser(PaperParser):
    """ The LpscParser removes special text content/format (e.g., LPSC
    conference header) from the two-page abstracts published at Lunar and
    Planetary Science Conference
    """
    PDF_TYPE = "application/pdf"

    def __init__(self, parser_name='lpsc_parser'):
        super(LpscParser, self).__init__(parser_name)

    def parse(self, text, metadata):
        paper_dict = super(LpscParser, self).parse(text, metadata)
        cleaned_text = paper_dict['cleaned_content']

        # Remove xxxx.PDF
        cleaned_text = re.sub(r'([0-9][0-9][0-9][0-9].PDF)', '', cleaned_text,
                              flags=re.IGNORECASE)
        # And "xx(th|st) Lunar and Planetary Science Conference ((19|20)xx)"
        cleaned_text = re.sub(r'([0-9][0-9].. Lunar and Planetary Science '
                              r'Conference \((19|20)[0-9][0-9]\)) ?', '',
                              cleaned_text, flags=re.IGNORECASE)
        # And "Lunar and Planetary Science XXXIII (2002)"
        # with Roman numeral and optional year
        cleaned_text = re.sub(r'(Lunar and Planetary Science '
                              r'[CDILVXM]+( \((19|20)[0-9][0-9]\))?) ?', '',
                              cleaned_text, flags=re.IGNORECASE)

        return {
            'references': paper_dict['references'],
            'cleaned_content': cleaned_text
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
