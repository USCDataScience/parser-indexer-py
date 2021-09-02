# MTE Parser Indexer

## Introduction
The MTE Parser Indexer contains 1 [base parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/parser.py) 
and 7 parsers created for different purposes.

[Base Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/parser.py):
The base parser that all parsers should inherit.

[TIKA Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/tika_parser.py): 
The TIKA parser utilizes Apache TIKA service to convert PDF files to text files. 

[ADS Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/ads_parser.py):
The ADS parser utilizes the search API of the Astrophysics Data System to extract information including title, author, 
primary author, affiliation, publication venue, and publication date.

[CoreNLP Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/corenlp_parser.py):
The CoreNLP parser utilizes the Named Entity Recognition (NER) sub module of the Stanford CoreNLP package to categorize 
words into named entities (e.g., target, mineral, element)

[JSRE Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/jsre_parser.py):
The JSRE parser utilizes the Java Simple Relation Extraction (JSRE) toolkit to extract relations between named entities.   

[Paper Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/paper_parser.py):
The Paper parser is a generic parser suitable for papers from all publication venues. The Paper parser is implemented to 
augment/remove contents (e.g., translate some UTF8 punctuation to ASCII, remove hyphenation at the end of lines, etc.) 
general to all papers.

[LPSC Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/lpsc_parser.py):
The LPSC parser is created for the two-page abstract from Lunar and Planetary Science Conference (LPSC). It utilizes 
regular expression matches to remove contents specific (e.g., abstract id, conference header) to the LPSC abstract. 

[JGR Parser](https://github.com/USCDataScience/parser-indexer-py/blob/master/src/parserindexer/jgr_parser.py):
The JGR parser is created for the papers from Journal of Geophysical Research. 


The class diagram of the parsers is shown below:

![MTE Parser class diagram](https://user-images.githubusercontent.com/57238811/125823293-50bef515-6713-4c2d-884e-da80810652e2.png)

## Usage
* TIKA Parser

```
>>> python tika_parser.py -h
usage: tika_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE
                      [-l LOG_FILE] [-p TIKA_SERVER_URL]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./tika-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL
```

Note that the `-p` TIKA_SERVER_URL argument is optional. The following command is an example of using TIKA parser:

```
python tika_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE
```

* ADS Parser

```
>>> python ads_parser.py -h
usage: ads_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE [-l LOG_FILE]
                     [-p TIKA_SERVER_URL] [-a ADS_URL] [-t ADS_TOKEN]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./ads-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL
  -a ADS_URL, --ads_url ADS_URL
                        ADS RESTful API. The ADS RESTful API should not need
                        to be changed frequently unless someting at the ADS is
                        changed.
  -t ADS_TOKEN, --ads_token ADS_TOKEN
                        The ADS token, which is required to use the ADS
                        RESTful API. The token was obtained using the
                        instructions at https://github.com/adsabs/adsabs-dev-
                        api#access. The ADS token should not need to be
                        changed frequently unless something at the ADS is
                        changed.
```

The example command is shown below:

```
python ads_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE
```

* CoreNLP Parser

```
>>> python corenlp_parser.py -h
usage: corenlp_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE
                         [-l LOG_FILE] [-p TIKA_SERVER_URL]
                         [-c CORENLP_SERVER_URL] [-n NER_MODEL] [-a ADS_URL]
                         [-t ADS_TOKEN]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./corenlp-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL
  -c CORENLP_SERVER_URL, --corenlp_server_url CORENLP_SERVER_URL
                        CoreNLP Server URL
  -n NER_MODEL, --ner_model NER_MODEL
                        Path to a Named Entity Recognition (NER) model
  -a ADS_URL, --ads_url ADS_URL
                        ADS RESTful API. The ADS RESTful API should not need
                        to be changed frequently unless someting at the ADS is
                        changed.
  -t ADS_TOKEN, --ads_token ADS_TOKEN
                        The ADS token, which is required to use the ADS
                        RESTful API. The token was obtained using the
                        instructions at https://github.com/adsabs/adsabs-dev-
                        api#access. The ADS token should not need to be
                        changed frequently unless something at the ADS is
                        changed.
```

The example command is shown below:

```
python ads_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE -n /PATH/TO/TRAINED/NER/MODEL
``` 

* JSRE Parser

```
>>> python jsre_parser.py -h
usage: jsre_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE
                      [-l LOG_FILE] [-p TIKA_SERVER_URL]
                      [-c CORENLP_SERVER_URL] [-n NER_MODEL] [-jr JSRE_ROOT]
                      -jm JSRE_MODEL [-jt JSRE_TMP_DIR] [-a ADS_URL]
                      [-t ADS_TOKEN]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./jsre-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL
  -c CORENLP_SERVER_URL, --corenlp_server_url CORENLP_SERVER_URL
                        CoreNLP Server URL
  -n NER_MODEL, --ner_model NER_MODEL
                        Path to a Named Entity Recognition (NER) model
  -jr JSRE_ROOT, --jsre_root JSRE_ROOT
                        Path to jSRE installation directory. Default is
                        /proj/mte/jSRE/jsre-1.1
  -jm JSRE_MODEL, --jsre_model JSRE_MODEL
                        Path to jSRE model
  -jt JSRE_TMP_DIR, --jsre_tmp_dir JSRE_TMP_DIR
                        Path to a directory for jSRE to temporarily store
                        input and output files. Default is /tmp
  -a ADS_URL, --ads_url ADS_URL
                        ADS RESTful API. The ADS RESTful API should not need
                        to be changed frequently unless someting at the ADS is
                        changed.
  -t ADS_TOKEN, --ads_token ADS_TOKEN
                        The ADS token, which is required to use the ADS
                        RESTful API. The token was obtained using the
                        instructions at https://github.com/adsabs/adsabs-dev-
                        api#access. The ADS token should not need to be
                        changed frequently unless something at the ADS is
                        changed.
```

The example command is shown below:

```
python jsre_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE -n /PATH/TO/TRAINED/NER/MODEL -jr /PATH/TO/TRAINED/JSRE/MODEL
```

* Paper Parser

```
>>> python paper_parser.py -h
usage: paper_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE
                       [-l LOG_FILE] [-p TIKA_SERVER_URL]
                       [-c CORENLP_SERVER_URL] [-n NER_MODEL] [-jr JSRE_ROOT]
                       -jm JSRE_MODEL [-jt JSRE_TMP_DIR] [-a ADS_URL]
                       [-t ADS_TOKEN]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./paper-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL
  -c CORENLP_SERVER_URL, --corenlp_server_url CORENLP_SERVER_URL
                        CoreNLP Server URL
  -n NER_MODEL, --ner_model NER_MODEL
                        Path to a Named Entity Recognition (NER) model
  -jr JSRE_ROOT, --jsre_root JSRE_ROOT
                        Path to jSRE installation directory. Default is
                        /proj/mte/jSRE/jsre-1.1
  -jm JSRE_MODEL, --jsre_model JSRE_MODEL
                        Path to jSRE model
  -jt JSRE_TMP_DIR, --jsre_tmp_dir JSRE_TMP_DIR
                        Path to a directory for jSRE to temporarily store
                        input and output files. Default is /tmp
  -a ADS_URL, --ads_url ADS_URL
                        ADS RESTful API. The ADS RESTful API should not need
                        to be changed frequently unless someting at the ADS is
                        changed.
  -t ADS_TOKEN, --ads_token ADS_TOKEN
                        The ADS token, which is required to use the ADS
                        RESTful API. The token was obtained using the
                        instructions at https://github.com/adsabs/adsabs-dev-
                        api#access. The ADS token should not need to be
                        changed frequently unless something at the ADS is
                        changed.
```

The example command is shown below:

```
python paper_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE -n /PATH/TO/TRAINED/NER/MODEL -jr /PATH/TO/TRAINED/JSRE/MODEL
```

* LPSC parser

```
python lpsc_parser.py -h
usage: lpsc_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE
                      [-l LOG_FILE] [-p TIKA_SERVER_URL]
                      [-c CORENLP_SERVER_URL] [-n NER_MODEL] [-jr JSRE_ROOT]
                      -jm JSRE_MODEL [-jt JSRE_TMP_DIR] [-a ADS_URL]
                      [-t ADS_TOKEN]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./lpsc-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL
  -c CORENLP_SERVER_URL, --corenlp_server_url CORENLP_SERVER_URL
                        CoreNLP Server URL
  -n NER_MODEL, --ner_model NER_MODEL
                        Path to a Named Entity Recognition (NER) model
  -jr JSRE_ROOT, --jsre_root JSRE_ROOT
                        Path to jSRE installation directory. Default is
                        /proj/mte/jSRE/jsre-1.1
  -jm JSRE_MODEL, --jsre_model JSRE_MODEL
                        Path to jSRE model
  -jt JSRE_TMP_DIR, --jsre_tmp_dir JSRE_TMP_DIR
                        Path to a directory for jSRE to temporarily store
                        input and output files. Default is /tmp
  -a ADS_URL, --ads_url ADS_URL
                        ADS RESTful API. The ADS RESTful API should not need
                        to be changed frequently unless someting at the ADS is
                        changed.
  -t ADS_TOKEN, --ads_token ADS_TOKEN
                        The ADS token, which is required to use the ADS
                        RESTful API. The token was obtained using the
                        instructions at https://github.com/adsabs/adsabs-dev-
                        api#access. The ADS token should not need to be
                        changed frequently unless something at the ADS is
                        changed.
```

The example command is shown below:

```
python lpsc_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE -n /PATH/TO/TRAINED/NER/MODEL -jr /PATH/TO/TRAINED/JSRE/MODEL
```

* JGR Parser

```
python jgr_parser.py -h
usage: jgr_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE [-l LOG_FILE]
                     [-p TIKA_SERVER_URL] [-c CORENLP_SERVER_URL]
                     [-n NER_MODEL] [-jr JSRE_ROOT] -jm JSRE_MODEL
                     [-jt JSRE_TMP_DIR] [-a ADS_URL] [-t ADS_TOKEN]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./jgr-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL
  -c CORENLP_SERVER_URL, --corenlp_server_url CORENLP_SERVER_URL
                        CoreNLP Server URL
  -n NER_MODEL, --ner_model NER_MODEL
                        Path to a Named Entity Recognition (NER) model
  -jr JSRE_ROOT, --jsre_root JSRE_ROOT
                        Path to jSRE installation directory. Default is
                        /proj/mte/jSRE/jsre-1.1
  -jm JSRE_MODEL, --jsre_model JSRE_MODEL
                        Path to jSRE model
  -jt JSRE_TMP_DIR, --jsre_tmp_dir JSRE_TMP_DIR
                        Path to a directory for jSRE to temporarily store
                        input and output files. Default is /tmp
  -a ADS_URL, --ads_url ADS_URL
                        ADS RESTful API. The ADS RESTful API should not need
                        to be changed frequently unless someting at the ADS is
                        changed.
  -t ADS_TOKEN, --ads_token ADS_TOKEN
                        The ADS token, which is required to use the ADS
                        RESTful API. The token was obtained using the
                        instructions at https://github.com/adsabs/adsabs-dev-
                        api#access. The ADS token should not need to be
                        changed frequently unless something at the ADS is
                        changed.
```

The example command is shown below:

```
python jgr_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE -n /PATH/TO/TRAINED/NER/MODEL -jr /PATH/TO/TRAINED/JSRE/MODEL
```

* Unary Parser: 

To install required packages, do the following: 

```
pip install torch
pip install sacremoses==0.0.38
pip install transformers==2.2.0
```

```
>>> python unary_parser.py -h
usage: unary_parser.py [-h] (-i IN_FILE | -li IN_LIST) -o OUT_FILE
                      [-l LOG_FILE] [-p TIKA_SERVER_URL] [-a ADS_URL]
                      [-t ADS_TOKEN]
                      [-c CORENLP_SERVER_URL] [-n NER_MODEL] [-cnte CONTAINEE_MODEL_FILE] [-cntr CONTAINER_MODEL_FILE] [-m ENTITY_LINKING_METHOD] [-g GPU_ID] [-b BATCH_SIZE]

optional arguments:
  -h, --help            show this help message and exit
  -i IN_FILE, --in_file IN_FILE
                        Path to input file
  -li IN_LIST, --in_list IN_LIST
                        Path to input list
  -o OUT_FILE, --out_file OUT_FILE
                        Path to output JSON file
  -l LOG_FILE, --log_file LOG_FILE
                        Log file that contains processing information. It is
                        default to ./jsre-parser-log.txt unless otherwise
                        specified.
  -p TIKA_SERVER_URL, --tika_server_url TIKA_SERVER_URL
                        Tika server URL 
  -a ADS_URL, --ads_url ADS_URL
                        ADS RESTful API. The ADS RESTful API should not need
                        to be changed frequently unless someting at the ADS is
                        changed.
  -t ADS_TOKEN, --ads_token ADS_TOKEN
                        The ADS token, which is required to use the ADS
                        RESTful API. The token was obtained using the
                        instructions at https://github.com/adsabs/adsabs-dev-
                        api#access. The ADS token should not need to be
                        changed frequently unless something at the ADS is
                        changed.
  -cnte CONTAINEE_MODEL_FILE, --containee_model_file CONTAINEE_MODEL_FILE 
                        Path to a trained Containee model
  -cntr CONTAINER_MODEL_FILE, --container_model_file CONTAINER_MODEL_FILE 
                        Path to a trained Container model
  -m {closest_container_closest_containee,closest_target_closest_component,closest_containee,closest_container,closest_component,closest_target}, --entity_linking_method {closest_container_closest_containee,closest_target_closest_component,closest_containee,closest_container,closest_component,closest_target}
                        Method to form relations between entities. [closest_containee]: for each Container instance, link it to its closest
                        Containee instance with a Contains relation, [closest_container]: for each Containee instance, link it to its closest
                        Container instance with a Contains relation, [closest_component]: for each Container instance, link it to its closest
                        Component instance with a Contains relation, [closest_target]: for each Containee instance, link it to its closest
                        Target instance with a Contains relation, [closest_target_closest_component]: union the relation instances found by closest_target and closest_component, [closest_container_closest_containee]: union the relation instances found by closest_containee and closest_container. This is the best method on the MTE test set
  -g GPU_ID, --gpu_id GPU_ID
                        GPU ID. If set to negative then no GPU would be used.
  -b BATCH_SIZE, --batch_size BATCH_SIZE
                        Batch size at inference time.
```

The example command is shown below:

```
python unary_parser.py -li /PATH/TO/LIST/OF/PDF/FILES -o /PATH/TO/OUTPUT/JSONL/FILE -l /PATH/TO/OUTPUT/LOG/FILE -n /PATH/TO/TRAINED/NER/MODEL -cnte /PATH/TO/CONTAINEE_FILE -cntr /PATH/TO/CONTAINER_FILE -m ENTITY_LINKING_METHOD -g GPU_ID
```
