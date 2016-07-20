# Parse and Index Journal papers


 This document contains steps to parse and index journals



## Step 1: Create a list of input paths of PDFs

 Create a text file containing paths of input pdfs.
 The format is plain text file which contains one path per file. Absolute path is recommended.

This can be easily done by `cd` to your PDF directory, run `find $PWD -name *.pdf > paths.txt`

 Sample :
```
../pdfs/1249.pdf
../pdfs/1369.pdf
../pdfs/1373.pdf
../pdfs/1413.pdf
../pdfs/1433.pdf
../pdfs/1438.pdf
../pdfs/1505.pdf
../pdfs/1510.pdf
../pdfs/1514.pdf
../pdfs/1524.pdf
```


## Step 2: Start Parser-Server and Grobid Server
 Refer to README inside `parser-server` sub directory


## Step 3: Parse the pdfs


#### Usage
```
usage: JournalParser [-h] [-v] (-i IN | -li LIST) -o OUT [-p PARSER_URL]

This tool can parse files.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -i IN, --in IN        Path to Input File.
  -li LIST, --list LIST
                        Path to a text file which contains list of input file
                        paths
  -o OUT, --out OUT     Path to output file.
  -p PARSER_URL, --parser-url PARSER_URL
                        URL of Tika Server.
```

#### Example :

Assumption: you have parser-server running at `http://localhost:9998` and it has
been configured to use grobid server.

```
 python journalparser.py -o out.jsonl -li paths.txt -p http://localhost:9998
```
Note :  if `-p http://localhost:9998` is not given, it will use default tika which
has not configured with journal parser.

This will crate a JSON line dump file


## Step 4: Index the dump to solr

### Step 4a. Start Solr :

Download Solr

    mkdir workspace && cd workspace
    wget http://archive.apache.org/dist/lucene/solr/6.1.0/solr-6.1.0.tgz
    tar xvzf solr-6.1.0.tgz
    cd solr-6.1.0

Start and Create a Core

    PORT=8983
    bin/solr start -p $PORT
    bin/solr create_core -c docs -d $YOUR_PATH/conf/solr/docs -p $PORT


### Step 4b. Index to Solr

`python indexer.py -h `

#### Usage :
```
usage: indexer.py [-h] [-v] -i IN -s SOLR_URL -sc SCHEMA

This tool can read JSON line dump and index to solr.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -i IN, --in IN        Path to Input JSON line file.
  -s SOLR_URL, --solr-url SOLR_URL
                        URL of Solr core.
  -sc SCHEMA, --schema SCHEMA
                        Schema Mapping to be used. Options: ['journal',
                        'basic']
```

#### Example:

Assumption: Solr is serving at http://localhost:8983/solr/ and a core named `docs` exists

`python indexer.py -i out.jsonl -s http://localhost:8983/solr/docs -sc basic`

NOTE: Only basic schema map is supported at this time.
