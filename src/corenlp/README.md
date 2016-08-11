# Training a custom Named Entity Recogniser using Stanford CoreNLP

This document contains instructions to train Core NLP's CRFClassifier for NER.

## References:
1. Create custom NER model for CoreNLP http://nlp.stanford.edu/software/crf-faq.shtml#a
2. Brat : http://brat.nlplab.org/
3. Py CoreNLP https://github.com/smilli/py-corenlp

## Step 1. Download CoreNLP
Visit http://stanfordnlp.github.io/CoreNLP/download.html,
download the zip.
Extract the zip.
Note: this runs on Java 8

## Step 2: Install Python dependencies

Follow instructions in https://github.com/smilli/py-corenlp

    pip install pycorenlp

## Step 3: Start Core NLP server
Goto CoreNLP extracted directory and runs

    java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer

## Step 4: Prepare input text and annotations
List all the `.txt` files and `.ann` files to a path list file

    $ ls $PWD/*.ann | sed -e 's/\(.*\)\.ann/\1.txt,\1.ann/g' > input.list
    

## Step 5: Separate the training and testing records

Split the `input.list` for training and testing data. Lets call them as `train.list` and `test.list`

## Step 6: Convert brat to corenlp NER format


    python3 brat2ner.py --in train.list --out train.tsv
    python3 brat2ner.py --in test.list --out test.tsv

## Step 6: Train and create a NER Model

Create a properties file lpsc.prop

```
#location of the training file
trainFile = train.tsv
#location where you would like to save (serialize to) your
#classifier; adding .gz at the end automatically gzips the file,
#making it faster and smaller
serializeTo = ner-model.ser.gz

#structure of your training file; this tells the classifier
#that the word is in column 0 and the correct answer is in
#column 1
map = word=0,answer=1

#these are the features we'd like to train with
#some are discussed below, the rest can be
#understood by looking at NERFeatureFactory
useClassFeature=true
useWord=true
useNGrams=true
#no ngrams will be included that do not contain either the
#beginning or end of the word
noMidNGrams=true
useDisjunctive=true
maxNGramLeng=6
usePrev=true
useNext=true
useSequences=true
usePrevSequences=true
maxLeft=1
#the next 4 deal with word shape features
useTypeSeqs=true
useTypeSeqs2=true
useTypeySequences=true
wordShape=chris2useLC
```

    java -cp .:../stanford-corenlp-full-2015-12-09/* \
     edu.stanford.nlp.ie.crf.CRFClassifier  -prop lpsc.prop

## Step 7: Test
    java -cp .:../stanford-corenlp-full-2015-12-09/* edu.stanford.nlp.ie.crf.CRFClassifier  -loadClassifier ner-model.ser.gz -testFile test.tsv
