# Parser-Indexer
This project contains tools for parsing files and indexing to solr. It also includes tools for information extraction.


For instructions related to training the custom Named Entity Recognition model using Stanford CoreNLP, visit [src/corenlp](src/corenlp)

## Requirements

1. Solr
2. Parser Server


### 1. Setting up solr

Download Solr

    mkdir workspace && cd workspace
    wget http://archive.apache.org/dist/lucene/solr/6.1.0/solr-6.1.0.tgz
    tar xvzf solr-6.1.0.tgz
    cd solr-6.1.0

Start and Create a Core

    PORT=8983
    bin/solr start -p $PORT
    bin/solr create_core -c docs -d $YOUR_PATH/conf/solr/docs -p $PORT



### 2. Parser Server

  Refer to README of `parser-server` in sub directory.



### Examples :

Checkout `docs` folder.

+ To parse and index jounrals : `docs/parser-index-journals.md`
