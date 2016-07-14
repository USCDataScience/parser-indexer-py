from __future__ import print_function

from argparse import ArgumentParser
from tika import parser as tkparser
import json


def parse_files(paths):
    """
    Parses stream of files and produces stream of parsed content
    :param paths: stream/list of file paths
    :return: stream of parsed content
    """
    for p in paths:
        try:
            yield tkparser.from_file(p)
        except Exception as e:
            print("Error: %s" % e)


def init(server_url=None):
    import tika
    tika.initVM()
    # TODO: init from srever_url


def dump_as_jsonlines(objects, filename):
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


if __name__ == '__main__':

    # Step : Parse CLI args
    parser = ArgumentParser(prog="Parser Indexer", description="This tool can parse files and index to solr.",
                            version="1.0")
    input_args = parser.add_mutually_exclusive_group(required=True)
    input_args.add_argument("-i", "--in", help="Path to Input File.")
    input_args.add_argument("-li", "--list", help="Path to a text file which contains list of input file paths")
    parser.add_argument("-o", "--out", help="Path to output file.", required=True)
    parser.add_argument("-p", "--parser-url", help="URL of Tika Server.", required=False)
    args = vars(parser.parse_args())
    print(args)

    # Step : Initialize Tika
    init(args['parser_url'])
    cleanups = []
    # get stream/list of files
    if args['list']:
        files = open(args['list'], 'rb')
        cleanups.append(lambda: files.close())
        files = filter(lambda x: x and not x.startswith("#"), map(lambda y: y.strip(), files))
    else:
        files = [args['in']]
    # Step : Parse
    parsed = parse_files(files)
    # Step store the objects to file
    dump_as_jsonlines(parsed, args['out'])

    for cl in cleanups:
        try:
            cl()
        except Exception:
            pass  # ignore
