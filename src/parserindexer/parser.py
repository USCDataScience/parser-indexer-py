from __future__ import print_function

from argparse import ArgumentParser
from tika import parser as tkparser
from ioutils import read_lines, dump_jsonlines
import os


class Parser(object):

    def __init__(self, server_url=None):
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
                print("Error: %s" % e)

    def parse_file(self, path):
        """
        Parses a file at given path
        :param path: path to file
        :return: parsed content
        """
        parsed = tkparser.from_file(path)
        parsed['file'] = os.path.abspath(path)
        return parsed


def main(parser_class):
    # Step : Parse CLI args
    parser = ArgumentParser(prog=parser_class.__name__, description="This tool can parse files.",
                            version="1.0")
    input_args = parser.add_mutually_exclusive_group(required=True)
    input_args.add_argument("-i", "--in", help="Path to Input File.")
    input_args.add_argument("-li", "--list", help="Path to a text file which contains list of input file paths")
    parser.add_argument("-o", "--out", help="Path to output file.", required=True)
    parser.add_argument("-p", "--parser-url", help="URL of Tika Server.", required=False)
    args = vars(parser.parse_args())

    # Step : Initialize Tika
    parser = parser_class(args['parser_url'])
    # get stream/list of files
    if args['list']:
        files = read_lines(args['list'])
    else:
        files = [args['in']]
    # Step : Parse
    parsed = parser.parse_files(files)
    # Step store the objects to file
    dump_jsonlines(parsed, args['out'])


if __name__ == '__main__':
    main(Parser)
