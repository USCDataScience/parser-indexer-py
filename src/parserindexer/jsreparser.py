from __future__ import print_function

import argparse
from argparse import ArgumentParser
import os, subprocess


class JsreParser(object):
    JSRE_PARSER = "org.itc.irst.tcc.sre.Predict"

    def __init__(self, **kwargs):
        self.jsre = kwargs['jsre']

    def set_classpath(self):
        jars = [ 'dist/xjsre.jar', 'lib/commons-beanutils.jar', 
                 'lib/commons-cli-1.0.jar', 'lib/commons-collections.jar',  
                 'lib/commons-digester.jar', 'lib/commons-logging.jar',  
                 'lib/libsvm-2.8.jar', 'lib/log4j-1.2.8.jar']

        os.environ['CLASSPATH'] = ':'.join(map(lambda x: 
                                               os.path.join(self.jsre, x), 
                                               jars))


    def predict(self, jsre_model, in_file, out_file):
        self.set_classpath()
        #print(os.environ['CLASSPATH'])
        cmd = ['java', '-mx256M', self.JSRE_PARSER, in_file, 
               jsre_model, out_file]
        #print(cmd)
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
