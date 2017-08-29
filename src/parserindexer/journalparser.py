from __future__ import print_function

from parser import *
from brat_ann_indexer import extract_references

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
        # Why would we check that it's already been parsed before doing so?
        #assert JournalParser._JOURNAL_PARSER in set(pdf_md['X-Parsed-By'])

        # Result of Tika parsing is in parsed['content']
        #content = parsed['content'].strip()
        #parsed['content'] = content # stripped off the whitespaces
        #assert type(content) == str or type(content) == unicode

        # Improve parsing and save in parsed['content_ann_s']
        content_ann = parsed['content']
        assert type(content_ann) == str or type(content_ann) == unicode

        #### New parsing (after extract_text_utf8.py)
        # 0. Translate some UTF-8 punctuation to ASCII
        punc = { 0x2018:0x27, 0x2019:0x27, # single quote
                 0x201C:0x22, 0x201D:0x22, # double quote
                 0x2010:0x2d, 0x2011:0x2d, 0x2012:0x2d, 0x2013:0x2d, # hyphens
                 0xFF0C:0x2c, # comma
                 0x00A0:0x20, # space
                 0x2219:0x2e, 0x2022:0x2e, # bullets
                 }
        content_ann = content_ann.translate(punc)

        # 1. Replace newlines that separate words with a space (unless hyphen)
        content_ann = re.sub(r'([^\s-])[\r|\n]+([^\s])','\\1 \\2', content_ann)

        # 2. Remove hyphenation at the end of lines 
        # (this is sometimes bad, as with "Fe-\nrich")
        content_ann = content_ann.replace('-\n','\n')

        # 3. Remove all newlines
        content_ann = re.sub(r'[\r|\n]+','', content_ann)

        # 4. Remove xxxx.PDF
        content_ann = re.sub(r'([0-9][0-9][0-9][0-9].PDF)', '', content_ann,
                         flags=re.IGNORECASE)
        # And "Lunar and Planetary Science Conference (201x)"
        content_ann = re.sub(r'([0-9][0-9].. Lunar and Planetary Science Conference \(201[0-9]\))', 
                         '', content_ann,
                         flags=re.IGNORECASE)

        # 5. Remove mailto: links
        content_ann = re.sub(r'mailto:[^\s]+','', content_ann)

        #print(content_ann)
        #raw_input()

        # 6. Move references to their own field (references)
        refs = extract_references(content_ann)
        for ref_id in refs:  # preserve length; insert whitespace
            content_ann = content_ann.replace(refs[ref_id],
                                              ' ' * len(refs[ref_id]))
        parsed['references'] = refs.values()

        # Store the modified content
        parsed['content_ann_s'] = content_ann

        # Find named entities
        self.parse_names(content_ann, pdf_md)
        #self.parse_names(content, pdf_md)

        return parsed

    def parse_names(self, content, meta):
        # Named Entity Parsing
        # Assumption : NER parser is enabled for text/plain
        text_feats = tkparser.from_buffer(content)
        ner_md = text_feats['metadata']
        assert JournalParser._NER_PARSER in set(ner_md['X-Parsed-By'])

        ner_keys = filter(lambda x: x.startswith('NER_'), ner_md.keys())
        for entity_type in ner_keys:
            meta[entity_type] = ner_md[entity_type]
        # Merged NER and Journal Parsers
        # This was NER_PARSER, which makes no sense.  Now JOURNAL_PARSER.
        meta['X-Parsed-By'].append(JournalParser._JOURNAL_PARSER)

if __name__ == '__main__':
    args = vars(CliParser(JournalParser).parse_args())
    main(JournalParser, args)
