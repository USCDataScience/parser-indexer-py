from __future__ import print_function

import os
import sys
import json
import tika
from tqdm import tqdm
from utils import LogUtil
from parser import Parser
from ioutils import read_lines
from tika import parser as tk_parser


class TikaParser(Parser):
    """ The TikaParser class is wrapper of the Apache TIKA parse """
    def __init__(self, tika_server_url):
        super(TikaParser, self).__init__('tika_parser')

        if tika_server_url:
            os.environ['TIKA_CLIENT_ONLY'] = 'True'
            os.environ['TIKA_SERVER_ENDPOINT'] = tika_server_url
            print("Tika Server Endpoint %s" %
                  os.environ['TIKA_SERVER_ENDPOINT'])
        tika.initVM()

    def parse(self, file_path):
        """ Parse one PDF file using Apache TIKA parser

        Args:
            file_path (str): Path to a PDF file
        Return:
            parsed content stored in a dictionary
        """
        if not os.path.exists(file_path):
            raise RuntimeError('%s error. File not found: %s' %
                               (self.parse_name, os.path.abspath(file_path)))

        try:
            tika_dict = tk_parser.from_file(file_path)
        except Exception:
            raise RuntimeError('Internal TIKA error occurred while parsing the '
                               'file: %s' % os.path.abspath(file_path))

        tika_dict['file'] = os.path.abspath(file_path)

        return tika_dict


def process(in_file, in_list, out_file, log_file, tika_server_url):
    # Log input parameters
    logger = LogUtil('lpsc-parser', log_file)
    logger.info('Input parameters')
    logger.info('in_file: %s' % in_file)
    logger.info('in_list: %s' % in_list)
    logger.info('out_file: %s' % out_file)
    logger.info('tika_server_url: %s' % tika_server_url)

    if in_file and in_list:
        print('[ERROR] in_file and in_list cannot be provided simultaneously')
        sys.exit(1)

    tika_parser = TikaParser(tika_server_url)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in tqdm(files):
        try:
            tika_dict = tika_parser.parse(f)

            out_f.write(json.dumps(tika_dict))
            out_f.write('\n')
        except Exception as e:
            logger.info('TIKA parser failed: %s' % os.path.abspath(f))
            logger.error(e)

    out_f.close()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    input_parser = parser.add_mutually_exclusive_group(required=True)

    input_parser.add_argument('-i', '--in_file', help='Path to input file')
    input_parser.add_argument('-li', '--in_list', help='Path to input list')
    parser.add_argument('-o', '--out_file', required=True,
                        help='Path to output JSON file')
    parser.add_argument('-l', '--log_file', default='./tika-parser-log.txt',
                        help='Log file that contains processing information. '
                             'It is default to ./tika-parser-log.txt unless '
                             'otherwise specified.')
    parser.add_argument('-p', '--tika_server_url', required=False,
                        help='Tika server URL')
    args = parser.parse_args()
    process(**vars(args))


if __name__ == '__main__':
    main()
