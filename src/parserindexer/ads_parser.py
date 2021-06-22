from __future__ import print_function

import sys
import json
import warnings
import requests
from ioutils import read_lines
from utils import progress_bar
from tika_parser import TikaParser

# For handling warnings as errors (i.e., warnings can be captured using
# try-except).
warnings.filterwarnings('error')


class AdsParser(TikaParser):
    """ The Ads parser class utilizes the RESTful API from the Astrophysics
    Data System (ADS) to extract the primary author, author list, author
    affiliations, publication venue.
    """
    def __init__(self, ads_token, ads_base_url, tika_server_url):
        super(AdsParser, self).__init__(tika_server_url)
        self.ads_token = ads_token
        self.ads_base_url = ads_base_url

    def query_ads_database(self, title):
        headers = {
            'Authorization': 'Bearer %s' % self.ads_token
        }

        params = (
            ('q', 'title:%s' % title),
            ('fl', 'first_author,author,aff,pubdate,year,pub')
        )

        response = requests.get(self.ads_base_url, headers=headers,
                                params=params)

        if response.status_code != 200:
            raise RuntimeError('Failed accessing ADS database. The HTTP code '
                               'is %d.\nURL: %s\nHTTP request headers: %s\n'
                               'HTTP request parameters: %s' %
                               (response.status_code, self.ads_base_url,
                                json.dumps(headers), json.dumps(params)))

        data = response.json()
        data_docs = data['response']['docs']
        ads_dict = dict()

        if len(data_docs) == 0:
            warnings.warn('0 document found in the ADS database')
            return ads_dict

        if len(data_docs) > 1:
            warnings.warn('There are multiple documents returned from the ADS '
                          'database, and we are using the first document.')

        data_docs = data_docs[0]

        ads_dict['primary_author'] = data_docs['first_author']
        ads_dict['author'] = data_docs['author']
        ads_dict['affiliation'] = data_docs['aff']
        ads_dict['pub_venue'] = data_docs['pub']
        ads_dict['pub_year'] = data_docs['year']
        ads_dict['pub_date'] = data_docs['pubdate']

        return ads_dict

    def parse(self, file_path):
        tika_dict = super(AdsParser, self).parse(file_path)

        # Get the title of the paper from grobid
        title = tika_dict['metadata']['grobid:header_Title']

        # Query the ADS database
        ads_dict = self.query_ads_database(title)

        if len(ads_dict) == 0:
            return tika_dict

        # Add ADS records to the dictionary returned from TIKA parser
        tika_dict['metadata']['ads:primary_author'] = ads_dict['primary_author']
        tika_dict['metadata']['ads:author'] = ads_dict['author']
        tika_dict['metadata']['ads:affiliation'] = ads_dict['affiliation']
        tika_dict['metadata']['ads:pub_venue'] = ads_dict['pub_venue']
        tika_dict['metadata']['ads:pub_year'] = ads_dict['pub_year']
        tika_dict['metadata']['ads:pub_date'] = ads_dict['pub_date']

        return tika_dict


def process(in_file, in_list, out_file, tika_server_url, ads_url, ads_token):
    if in_file and in_list:
        print('[ERROR] in_file and in_list cannot be provided simultaneously')
        sys.exit(1)

    ads_parser = AdsParser(ads_token, ads_url, tika_server_url)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    progress = progress_bar('ADS parser')
    for f in progress(files):
        ads_dict = ads_parser.parse(f)

        out_f.write(json.dumps(ads_dict))
        out_f.write('\n')

    out_f.close()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    input_parser = parser.add_mutually_exclusive_group(required=True)

    input_parser.add_argument('-i', '--in_file', help='Path to input file')
    input_parser.add_argument('-li', '--in_list', help='Path to input list')
    parser.add_argument('-o', '--out_file', required=True,
                        help='Path to output JSON file')
    parser.add_argument('-p', '--tika_server_url', required=False,
                        help='Tika server URL')
    parser.add_argument('-a', '--ads_url',
                        default='https://api.adsabs.harvard.edu/v1/search/query',
                        help='ADS RESTful API. The ADS RESTful API should not '
                             'need to be changed frequently unless someting at '
                             'the ADS is changed.')
    parser.add_argument('-t', '--ads_token',
                        default='jON4eu4X43ENUI5ugKYc6GZtoywF376KkKXWzV8U',
                        help='The ADS token, which is required to use the ADS '
                             'RESTful API. The token was obtained using the '
                             'instructions at '
                             'https://github.com/adsabs/adsabs-dev-api#access. '
                             'The ADS token should not need to be changed '
                             'frequently unless something at the ADS is '
                             'changed.')

    args = parser.parse_args()
    process(**vars(args))


if __name__ == '__main__':
    main()
