# Parser-Server

This projects includes configurations and machine learning models required for
 enabling some of the advanced features of Apache Tika via REST Server


# Requirements and Setup instructions :

### 1. JDK 8 - Stanford CoreNLP will not run on older JDK

### 2. Tika Core NLP addon :

```
git clone https://github.com/thammegowda/tika-ner-corenlp.git
cd tika-ner-corenlp
mvn clean compile && mvn install
```

### 3. Grobid Server :

Full details at https://wiki.apache.org/tika/GrobidJournalParser
Follow these steps for a head start

```
git clone https://github.com/kermitt2/grobid.git
cd grobid
mvn install
cd grobid-service
mvn -Dmaven.test.skip=true jetty:run-war
```

### 4. Build parser-server

```
cd {parser-server}
mvn clean compile assembly:single
```

### 5. Launch Parser server

```
./run.sh
```
