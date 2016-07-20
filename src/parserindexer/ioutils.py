import json


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


def read_jsonlines(filename):
    """
    reads json lines
    :param filename: path to dump file
    :return: stream of dictionary objects
    """
    with open(filename, 'rb') as lines:
        for line in lines:
            yield json.loads(line)


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
