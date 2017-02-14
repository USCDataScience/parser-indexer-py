#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

CONF="$DIR/src/main/resources/tika-config.xml"
EXTRAS=""

usage() { echo "Usage: $0 [-m <./corenlp-ner-model.ser.gz>] [-c $CONF]" 1>&2; exit 1; }

while getopts ":m:c:" o; do
    case "${o}" in
        m)
            EXTRAS="${EXTRAS} -Dner.corenlp.model=${OPTARG}"
            ;;
        c)
            CONF=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
echo "JVM Extras  =$EXTRAS"
echo "Tika Config =$CONF"

# Assuming JAR is already built
java -Dner.impl.class=org.apache.tika.parser.ner.corenlp.CoreNLPNERecogniser,org.apache.tika.parser.ner.regex.RegexNERecogniser \
  ${EXTRAS} \
  -jar $DIR/target/parser-server-*-jar-with-dependencies.jar \
  -c "$CONF"
