from __future__ import print_function

from argparse import ArgumentParser
from tika import parser as tkparser
import json
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


def read_lines(listfile, skip_blank=True, skip_comments=True):
    """
    Reads lines from a list file
    :param listfile: a file having strings, one per line
    :param skip_blank:
    :param skip_comments:
    :return:
    """
    with open(listfile, 'rb') as paths:
        paths = map(lambda x: x.strip(), paths)
        if skip_blank:
            paths = filter(lambda x: x, paths)
        if skip_comments:
            paths = filter(lambda x: not x.startswith("#"), paths)
        for p in paths:
            yield p


def dump_jsonlines(objects, filename):
    """
    Stores objects into file in JSON line format.
    :param objects: stream of objects to be dumped
    :param filename: path of output file
    :return: number of objects dumped, which is same as number of lines stored
    """
    count = 0
    print("Writing to %s" % filename)
    with open(filename, 'wb', 1) as out:
        for obj in objects:
            out.write(json.dumps(obj))
            out.write("\n")
            count += 1
    print("Stored %d objects to %s" % (count, filename))
    return count


def main(parser_class):
    # Step : Parse CLI args
    parser = ArgumentParser(prog="Parser Indexer", description="This tool can parse files and index to solr.",
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
