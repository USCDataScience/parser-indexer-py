from __future__ import print_function

import argparse
from argparse import ArgumentParser
import os, subprocess


class JsreParser(object):

    def __init__(self, **kwargs):
        self.jsre = kwargs['jsre']
        self.jsre_model = kwargs['jsre_model']

    def set_classpath(self):
        os.environ['CLASSPATH'] = os.path.join(self.jsre, 'dist/xjsre.jar') + ':' + \
                                  os.path.join(self.jsre, 'lib/commons-beanutils.jar') + ':' + \
                                  os.path.join(self.jsre, 'lib/commons-cli-1.0.jar') + ':' + \
                                  os.path.join(self.jsre, 'lib/commons-collections.jar') + ':' + \
                                  os.path.join(self.jsre, 'lib/commons-digester.jar') + ':' + \
                                  os.path.join(self.jsre, 'lib/commons-logging.jar') + ':' + \
                                  os.path.join(self.jsre, 'lib/libsvm-2.8.jar') + ':' + \
                                  os.path.join(self.jsre, 'lib/log4j-1.2.8.jar')

    def predict(self, in_file, out_file):
        self.set_classpath()
        cmd = ['java', '-mx256M', 'org.itc.irst.tcc.sre.Predict', in_file, self.jsre_model, out_file]
        FNULL = open(os.devnull, 'w')
        subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)
        FNULL.close()

    def results(self, out_file):
        with open(out_file, 'rb') as res:
            for line in res.readlines():
                print(line.strip())


class CliParser(ArgumentParser):
    def __init__(self, parser_class):
        # Step : Parse CLI args
        super(CliParser, self).__init__(prog=parser_class.__name__,
            description="jSRE parser.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            version="1.0")
        self.add_argument("-li", "--list", help="Path to a text file which contains list of jSRE relation examples", required=True)
        self.add_argument("-o", "--out", help="Path to output file.", required=True)
        self.add_argument("-j", "--jsre", help="Path to jSRE installation directory.", required=True)
        self.add_argument("-m", "--jsre-model", help="Path to jSRE model.", required=True)


def main(parser_class, args):
    # Step : Initialize
    parser = parser_class(**args)
    # Step : Predict relations
    parser.predict(args['list'], args['out'])
    # Step : Print Results
    parser.results(args['out'])


if __name__ == '__main__':
    cli_p = CliParser(JsreParser)
    args = vars(cli_p.parse_args())
    main(JsreParser, args)
