#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Assuming JAR is already built
java -Dner.impl.class=org.apache.tika.parser.ner.corenlp.CoreNLPNERecogniser,org.apache.tika.parser.ner.regex.RegexNERecogniser \
  -jar $DIR/target/parser-server-*-jar-with-dependencies.jar \
  -c $DIR/src/main/resources/tika-config.xml
