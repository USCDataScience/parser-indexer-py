from __future__ import print_function

import argparse
from argparse import ArgumentParser

from tika import parser as tkparser
from ioutils import read_lines, dump_jsonlines
import os, sys, traceback, re


class Parser(object):

    def __init__(self, **kwargs):
        server_url = kwargs['tika_url']
        if server_url:
            os.environ['TIKA_CLIENT_ONLY'] = 'True'
            os.environ['TIKA_SERVER_ENDPOINT'] = server_url
            print("Tika Server Endpoint %s" % os.environ['TIKA_SERVER_ENDPOINT'])
        import tika
        tika.initVM()

    def parse_files(self, paths):
        """
        Parses stream of files and produces stream of parsed content
        :param paths: stream/list of file paths
        :return: stream of parsed content
        """
        for p in paths:
            try:
                yield self.parse_file(p)
            except Exception as e:
                print("Exception in user code:")
                print('-'*60)
                traceback.print_exc(file=sys.stdout)
                print('-'*60)

    def parse_file(self, path):
        """
        Parses a file at given path
        :param path: path to file
        :return: parsed content
        """
        if not os.path.exists(path):
            print('Error: Could not find PDF file %s.' % path)
            sys.exit(1)

        try:
            parsed = tkparser.from_file(path)
        except:
            print('Error: Could not parse PDF file %s.' % path)
            sys.exit(1)
        parsed['file'] = os.path.abspath(path)
        return parsed


class CliParser(ArgumentParser):
    def __init__(self, parser_class):
        # Step : Parse CLI args
        super(CliParser, self).__init__(prog=parser_class.__name__,
            description="This tool can parse files.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            version="1.0")
        input_args = self.add_mutually_exclusive_group(required=True)
        input_args.add_argument("-i", "--in", help="Path to Input File.")
        input_args.add_argument("-li", "--list", help="Path to a text file which contains list of input file paths")
        self.add_argument("-o", "--out", help="Path to output file.", required=True)
        self.add_argument("-p", "--tika-url", help="URL of Tika Server.", required=False)

def main(parser_class, args):

    # Step : Initialize Tika
    parser = parser_class(**args)
    # get stream/list of files
    if args['list']:
        if not os.path.exists(args['list']):
            print('Error: Could not find file containing input paths %s.' % 
                  args['list'])
            sys.exit(1)
        files = read_lines(args['list'])
    else:
        if not os.path.exists(args['in']):
            print('Error: Could not find input PDF file %s.' % 
                  args['in'])
            sys.exit(1)
        files = [args['in']]
    # Step : Parse
    parsed = parser.parse_files(files)
    # Step store the objects to file
    dump_jsonlines(parsed, args['out'])

if __name__ == '__main__':
    args = vars(CliParser(Parser).parse_args())
    main(Parser, args)
