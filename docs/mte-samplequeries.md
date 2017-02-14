# Solr Query Examples for Mars Target Encyclopedia index

This document provides sample queries for Mars Target Encyclopedia Index
The schema file can be seen in [../conf/solr/docs/conf/managed-schema](../conf/solr/docs/conf/managed-schema)

## Sample Queries


+ Query all documents : `http://localhost:8983/solr/docs/query?q=type:doc`
+ Query all documents with all annotations nested:  `http://localhost:8983/solr/docs/query?q=type:doc&fl=*,[child%20parentFilter=type:doc%20limit=10000]`

+ Get all details of a single document:
  `http://localhost:8983/solr/docs/query?q=type:doc&fl=*,[child%20parentFilter=type:doc%20limit=10000]&fq=id:1249`

+ Get all CoreNLP annotation for a document:
  `http://localhost:8983/solr/docs/query?q=type:doc&fl=id,[child%20parentFilter=type:doc%20childFilter=source:corenlp%20limit=1000]&fq=id:1249`

+ Get all CoreNLP annotations of type `target`
  `http://localhost:8983/solr/docs/query?q=type:doc&fl=id,[child%20parentFilter=type:doc%20childFilter=%22source:corenlp%20AND%20type:target%22%20limit=1000]&fq=id:1249`

---

## Auto completion / suggestions

  + get suggestions for 'wind'
  `http://localhost:8983/solr/docs/suggest?wt=json&q=wind`
  ```json
  "wind": {
      "numFound": 5,
      "suggestions": [
        {
        "term": "Windjana",
        "weight": 0,
        "payload": ""
        },
        {
        "term": "WINDJANA",
        "weight": 0,
        "payload": ""
        },
        {
        "term": "Windjanas",
        "weight": 0,
        "payload": ""
        },
      ]
    }
  ```

---

## Facets
+  Get Statistics about annotation types:
`http://localhost:8983/solr/docs/query?rows=0&q=_depth:1&facet=true&facet.field=type`

```json
 "type": [
    "element",
    3329,
    "mineral",
    1090,
    "target",
    1015,
    "contains",
    332,
    "shows",
    202
  ]
```

+ Statistics about annotation types from corenlp annotations only:
`http://localhost:8983/solr/docs/query?rows=0&q=_depth:1%20AND%20source:corenlp&facet=true&facet.field=type&facet.limit=5`

+ Stats for target annotations from CoreNLP
`http://localhost:8983/solr/docs/query?rows=0&q=_depth:1%20AND%20source:corenlp%20AND%20type:target&facet=true&facet.field=name&facet.limit=5`

```json
"name": [
  "Windjana",
  87,
  "Stephen",
  47,
  "Cumberland",
  25,
  "Dillinger",
  25,
  "Darwin",
24
]
```

More reference here https://cwiki.apache.org/confluence/display/solr/Faceting

---
# Free text search
+ Get all documents matching to term "Manganese" :  `http://localhost:8983/solr/docs/query?q=type:doc&fq=Manganese`


More referece here https://cwiki.apache.org/confluence/display/solr/Common+Query+Parameters

---
## Delete or clear the index

+ Caution: this will erase all docs in index

   `http://localhost:8983/solr/docs/update?stream.body=<delete><query>*:*</query></delete>&commit=true`
