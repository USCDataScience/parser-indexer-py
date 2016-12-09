from __future__ import print_function

from parser import *

class JournalParser(Parser):
    """
    This class a specialized parser for parsing Journals which are in PDF format
    """
    _JOURNAL_PARSER = 'org.apache.tika.parser.journal.JournalParser'
    _NER_PARSER = 'org.apache.tika.parser.ner.NamedEntityParser'
    _PDF_TYPE = "application/pdf"

    def parse_file(self, path):
        """
        Parses Journal files
        :param path:
        :return:
        """
        # Assumption : (1) Gobrid parser is enabled for PDFs
        #              (2) NER is not enabled for PDFs, so an additional parse step is required on text
        #              (3) Input file is a PDF
        parsed = super(JournalParser, self).parse_file(path)
        pdf_md = parsed['metadata']
        assert pdf_md['Content-Type'] == JournalParser._PDF_TYPE
        assert JournalParser._JOURNAL_PARSER in set(pdf_md['X-Parsed-By'])

        content = parsed['content'].strip()
        parsed['content'] = content # stripped off the whitespaces
        assert type(content) == str or type(content) == unicode
        self.parse_names(content, pdf_md)
        return parsed

    def parse_names(self, content, meta):
        # Named Entity Parsing
        # Assumption : NER parser is enabled for text/plain
        text_feats = tkparser.from_buffer(content)
        ner_md = text_feats['metadata']
        assert JournalParser._NER_PARSER in set(ner_md['X-Parsed-By'])

        ner_keys = filter(lambda x: x.startswith('NER_'), ner_md.keys())
        for entity_type in ner_keys:
            pdf_md[entity_type] = ner_md[entity_type]
        # Merged NER and Journal Parsers
        pdf_md['X-Parsed-By'].append(JournalParser._NER_PARSER)

if __name__ == '__main__':
    args = vars(CliParser(JournalParser).parse_args())
    main(JournalParser, args)
