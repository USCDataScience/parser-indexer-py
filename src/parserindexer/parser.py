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
        parsed = tkparser.from_file(path)
        content = parsed['content']

        # Extract references from the parsed content
        references = self.extract_references(content)

        # Remove references from the parsed content
        for ref_id in references:
            content = content.replace(references[ref_id], '')
        parsed['content'] = content

        if references:
            parsed['metadata']['references'] = references.values()
        parsed['file'] = os.path.abspath(path)
        return parsed

    def extract_references(self, content):
        """
        Extract references from text
        :param content: text
        :return: dictionary of references with reference id ([N]) as key
        """
        references = {}
        content = content.replace("\n", "\\n")
        matches = re.findall('(\[[0-9]+\][^\[]*?(?=\[|Acknowledge|Fig|Table|Conclusion|pdf))', content)
        if matches:
            for match in matches:
                ref_id = self.get_reference_id(match)
                # No reference id exist -- skip it
                if ref_id != -1:
                    value = match.replace('\\n', '\n')
                    references[ref_id] = value
        return references

    def get_reference_id(self, reference):
        """
        Extract reference id ([N])
        :param reference: Any possible reference
        :return: reference id
        """
        ref_id = -1
        match = re.search('\[[0-9]+\]', reference)
        if match:
            ref_id = int(match.group(0).strip('[]'))
        return ref_id


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
        files = read_lines(args['list'])
    else:
        files = [args['in']]
    # Step : Parse
    parsed = parser.parse_files(files)
    # Step store the objects to file
    dump_jsonlines(parsed, args['out'])

if __name__ == '__main__':
    args = vars(CliParser(Parser).parse_args())
    main(Parser, args)
