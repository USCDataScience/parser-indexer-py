# Setup Solr  
Download Solr

    mkdir workspace && cd workspace
    wget http://archive.apache.org/dist/lucene/solr/6.1.0/solr-6.1.0.tgz
    tar xvzf solr-6.1.0.tgz
    cd solr-6.1.0

Start and Create a Core

    PORT=8983
    bin/solr start -p $PORT
    bin/solr create_core -c docs -d $YOUR_PATH/conf/solr/docs -p $PORT

  To confirm solr setup completion, visit `http://<host>:8983/solr/`

# Index Brat annotations
In this step, we will index all the manual annotations from brat.
## Create an input file
Input file must be a CSV file containing one record per line.
Each line should have a path to .txt file and a path to .ann file in the same order (i.e. `a.txt,a.ann`)
```
find <dir> -name *.ann | sed 's/\(.*\)\.ann/\1.txt,\1.ann/g' > ann_recs.csv
```

The next step is to call `brat_ann_indexer.py` program and tell it to index the annotations into solr.
The arguments are:
```
$ python brat_ann_indexer.py  -h
usage: brat_ann_indexer.py [-h] -i IN [-s SOLR_URL]

optional arguments:
  -h, --help            show this help message and exit
  -i IN, --in IN        Path to input csv file having .txt,.ann records
  -s SOLR_URL, --solr-url SOLR_URL
```

Example :  
```
python brat_ann_indexer.py -s http://localhost:8983/solr/docs -i recs.csv
```

# Parse PDFs using Tika, Grobid and CoreNLP
This step has some additional setup. Refer to the README in `parser-server` directory for setting up parser server.
when the parser server is running on `http://localhost:9998/` follow the below steps:

Additional Setup :
Download and Start Stanford CoreNLP Server on port `:9000`
### Step . Download CoreNLP
Visit http://stanfordnlp.github.io/CoreNLP/download.html,
download the zip.
Extract the zip.
Note: this runs on Java 8

### Step : Install Python dependencies

Follow instructions in https://github.com/smilli/py-corenlp

```
pip install pycorenlp
```

### Step : Start Core NLP server
Goto CoreNLP extracted directory and run  
```
java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer
```

### Step: Re parse the PDFS using CoreNLP Parser
List all the PDFs to a list file  
```
find <dir> -name *.pdf > pdfpaths.list
```

Parse PDFs:

```
14:47 $ python corenlpparser.py -h
usage: CoreNLPParser [-h] [-v] (-i IN | -li LIST) -o OUT [-p TIKA_URL]
                     [-c CORENLP_URL] [-n NER_MODEL]

This tool can parse files.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -i IN, --in IN        Path to Input File. (default: None)
  -li LIST, --list LIST
                        Path to a text file which contains list of input file
                        paths (default: None)
  -o OUT, --out OUT     Path to output file. (default: None)
  -p TIKA_URL, --tika-url TIKA_URL
                        URL of Tika Server. (default: None)
  -c CORENLP_URL, --corenlp-url CORENLP_URL
                        CoreNLP Server URL (default: http://localhost:9000)
  -n NER_MODEL, --ner-model NER_MODEL
                        Path (on Server side) to NER model (default: None)
```
NOTE:
This expects three services to be running on its default ports: CoreNlpServer(:9000), Parser-Server (aka Tika Server :9998), Grobid Server (:8080)
Example:
```
$ python corenlpparser.py -li  pdfpaths.list \
  -o parsed-tika-grobid-corenlp.jl \
  -n <abspath>/ner-model-jpl-chemistry.ser.gz
```

# Update the parsed documents
In this step we update the solr index with the json line dump produced in the previous step.
Usage:
```
$ python indexer.py -h
usage: indexer.py [-h] [-v] -i IN [-s SOLR_URL] [-sc SCHEMA] [-u]

This tool can read JSON line dump and index to solr.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -i IN, --in IN        Path to Input JSON line file. (default: None)
  -s SOLR_URL, --solr-url SOLR_URL
                        URL of Solr core. (default:
                        http://localhost:8983/solr/docs)
  -sc SCHEMA, --schema SCHEMA
                        Schema Mapping to be used. Options: ['journal',
                        'basic'] (default: journal)
  -u, --update          Update documents in the index (default: False)
```

Example:
```
python indexer.py -i parsed-tika-grobid-corenlp.jl -u
```
NOTE:
Option `-u` will update the documents (thus it preserves the brat annotations which were previously added).
 Not specifying this option will overwrite the documents.


# Index Analyst's notebook targets:

In this step, we use `csvindexer.py` to index the csv file.
### Usage
```
usage: csvindexer.py [-h] [-v] -i IN [-s SOLR_URL] -t TYPE [-if ID_FIELD]

This tool can index CSV files to solr.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -i IN, --in IN        Path to input csv file (default: None)
  -s SOLR_URL, --solr-url SOLR_URL
                        Solr URL (default: http://localhost:8983/solr/docs)
  -t TYPE, --type TYPE  document type (default: None)
  -if ID_FIELD, --id-field ID_FIELD
                        ID field (default: None)
```

Example:
```
python csvindexer.py  -i .../ref/2016-0816-MSL-AN-Target-table.csv -t AN_target
```
