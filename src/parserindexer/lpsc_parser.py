from __future__ import print_function

from parser import *
from brat_ann_indexer import extract_references


class LpscParser(Parser):
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
        #              (2) NER is not enabled for PDFs, so an additional parse
        #              step is required on text
        #              (3) Input file is a PDF
        parsed = super(LpscParser, self).parse_file(path)
        pdf_md = parsed['metadata']
        if type(pdf_md['Content-Type']) == list:
            assert LpscParser._PDF_TYPE in pdf_md['Content-Type']
        else:
            assert pdf_md['Content-Type'] == LpscParser._PDF_TYPE

        # Improve parsing and save in parsed['content_ann_s']
        content_ann = parsed['content']
        assert type(content_ann) == str or type(content_ann) == unicode

        # New parsing (after extract_text_utf8.py)
        # 0. Translate some UTF-8 punctuation to ASCII
        punc = {
            # single quote
            0x2018: 0x27, 0x2019: 0x27,
            # double quote
            0x201C: 0x22, 0x201D: 0x22,
            # hyphens
            0x2010: 0x2d, 0x2011: 0x2d, 0x2012: 0x2d, 0x2013: 0x2d,
            # comma
            0xFF0C: 0x2c,
            # space
            0x00A0: 0x20,
            # bullets
            0x2219: 0x2e, 0x2022: 0x2e,
        }
        content_ann = content_ann.translate(punc)

        # 1. Replace newlines that separate words with a space (unless hyphen)
        content_ann = re.sub(r'([^\s-])[\r|\n]+([^\s])', '\\1 \\2', content_ann)

        # 2. Remove hyphenation at the end of lines 
        # (this is sometimes bad, as with "Fe-\nrich")
        content_ann = content_ann.replace('-\n', '\n')

        # 3. Remove all newlines
        content_ann = re.sub(r'[\r|\n]+', '', content_ann)

        # 4. Remove xxxx.PDF
        content_ann = re.sub(r'([0-9][0-9][0-9][0-9].PDF)', '', content_ann,
                         flags=re.IGNORECASE)
        # And "xx(th|st) Lunar and Planetary Science Conference ((19|20)xx)"
        content_ann = re.sub(r'([0-9][0-9].. Lunar and Planetary Science Conference \((19|20)[0-9][0-9]\)) ?', 
                             '', content_ann, flags=re.IGNORECASE)
        # And "Lunar and Planetary Science XXXIII (2002)"
        # with Roman numeral and optional year
        content_ann = re.sub(r'(Lunar and Planetary Science [CDILVXM]+( \((19|20)[0-9][0-9]\))?) ?', 
                             '', content_ann, flags=re.IGNORECASE)

        # 5. Remove mailto: links
        content_ann = re.sub(r'mailto:[^\s]+', '', content_ann)

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

        return parsed

    def parse_names(self, content, meta):
        # Named Entity Parsing
        # Assumption : NER parser is enabled for text/plain
        text_feats = tkparser.from_buffer(content)
        ner_md = text_feats['metadata']
        assert LpscParser._NER_PARSER in set(ner_md['X-Parsed-By'])

        ner_keys = filter(lambda x: x.startswith('NER_'), ner_md.keys())
        for entity_type in ner_keys:
            meta[entity_type] = ner_md[entity_type]
        # Merged NER and Journal Parsers
        # This was NER_PARSER, which makes no sense.  Now JOURNAL_PARSER.
        meta['X-Parsed-By'].append(LpscParser._JOURNAL_PARSER)


if __name__ == '__main__':
    args = vars(CliParser(LpscParser).parse_args())
    main(LpscParser, args)
