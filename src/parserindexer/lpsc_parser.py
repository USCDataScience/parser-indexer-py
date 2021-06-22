from __future__ import print_function

import os
import re
import sys
import json
from tqdm import tqdm
from utils import LogUtil
from ioutils import read_lines
from paper_parser import PaperParser
from ads_parser import AdsParser
from jsre_parser import JsreParser
from brat_ann_indexer import extract_references


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
                              r'[CDILVXM]+ (\((19|20)[0-9][0-9]\))?) ?', '',
                              cleaned_text, flags=re.IGNORECASE)

        # Extract references
        refs = extract_references(text)

        return {
            'references': refs.values(),
            'cleaned_content': cleaned_text
        }


def process(in_file, in_list, out_file, log_file, tika_server_url,
            corenlp_server_url, ner_model, jsre_root, jsre_model, jsre_tmp_dir,
            ads_url, ads_token):
    # Log input parameters
    logger = LogUtil('lpsc-parser', log_file)
    logger.info('Input parameters')
    logger.info('in_file: %s' % in_file)
    logger.info('in_list: %s' % in_list)
    logger.info('out_file: %s' % out_file)
    logger.info('tika_server_url: %s' % tika_server_url)
    logger.info('corenlp_server_url: %s' % corenlp_server_url)
    logger.info('ner_model: %s' % os.path.abspath(ner_model))
    logger.info('jsre_root: %s' % os.path.abspath(jsre_root))
    logger.info('jsre_model: %s' % os.path.abspath(jsre_model))
    logger.info('jsre_tmp_dir: %s' % os.path.abspath(jsre_tmp_dir))
    logger.info('ads_url: %s' % ads_url)
    logger.info('ads_token: %s' % ads_token)

    if in_file and in_list:
        logger.info('[ERROR] in_file and in_list cannot be provided '
                    'simultaneously')
        sys.exit(1)

    ads_parser = AdsParser(ads_token, ads_url, tika_server_url)
    lpsc_parser = LpscParser()
    jsre_parser = JsreParser(corenlp_server_url, ner_model, jsre_root,
                             jsre_model, jsre_tmp_dir)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in tqdm(files):
        logger.info('Processing %s' % os.path.basename(f))
        try:
            ads_dict = ads_parser.parse(f)
            lpsc_dict = lpsc_parser.parse(ads_dict['content'],
                                          ads_dict['metadata'])
            jsre_dict = jsre_parser.parse(lpsc_dict['cleaned_content'])

            ads_dict['content_ann_s'] = lpsc_dict['cleaned_content']
            ads_dict['references'] = lpsc_dict['references']
            ads_dict['metadata']['ner'] = jsre_dict['ner']
            ads_dict['metadata']['rel'] = jsre_dict['relation']
            ads_dict['metadata']['sentences'] = jsre_dict['sentences']
            ads_dict['metadata']['X-Parsed-By'] = jsre_dict['X-Parsed-By']

            out_f.write(json.dumps(ads_dict))
            out_f.write('\n')
        except Exception as e:
            logger.info('LPSC parser failed: %s' % os.path.abspath(f))
            logger.error(e)

    out_f.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    input_parser = parser.add_mutually_exclusive_group(required=True)

    input_parser.add_argument('-i', '--in_file', help='Path to input file')
    input_parser.add_argument('-li', '--in_list', help='Path to input list')
    parser.add_argument('-o', '--out_file', required=True,
                        help='Path to output JSON file')
    parser.add_argument('-l', '--log_file', default='./lpsc-parser-log.txt',
                        help='Log file that contains processing information. '
                             'It is default to ./lpsc-parser-log.txt unless '
                             'otherwise specified.')
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
