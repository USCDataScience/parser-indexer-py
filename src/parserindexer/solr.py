import json
import requests
import time

__author__ = 'Thamme Gowda N'

'''
This module offers solr client.
Created on November 20, 2015
'''


def current_milli_time(): return int(round(time.time() * 1000))


class Solr(object):
    """
    Solr client  for querying, posting and committing
    """

    def __init__(self, solr_url):
        self.update_url = solr_url + '/update/json'
        self.query_url = solr_url + '/select'
        self.headers = {"content-type": "application/json"}
        self.posted_items = 0

    def post_items(self, items, commit=False, softCommit=False):
        """ post list of items to Solr;
        """
        url = self.update_url
        # Check either to do soft commit or hard commit
        if commit:
            url += '?commit=true'
        elif softCommit or 'soft' == commit:
            url += '?softCommit=true'

        resp = requests.post(
            url,
            data=json.dumps(items).encode('utf-8', 'replace'),
            headers=self.headers)

        if not resp or resp.status_code != 200:
            print('Solr posting failed:', resp)
            return False
        return True

    def post_iterator(self, iter, commit=False, softCommit=False, buffer_size=100,
                      progress_delay=2000):
        """
        Posts all the items yielded by the input iterator to Solr;
        The documents will be buffered and sent in batches
        :param iter: generator that yields documents
        :param commit: commit after each batch? default is false
        :param softCommit: soft commit after each call ? default is false
        :param buffer_size: number of docs to buffer and post at once
        :param progress_delay: the number of milliseconds of
        :return: (numDocs, True) on success, (numDocs, False) on failure
        """
        buffer = []
        count = 0
        num_docs = 0
        tt = current_milli_time()
        for doc in iter:
            num_docs += 1
            buffer.append(doc)

            if len(buffer) >= buffer_size:
                # buffer full, post them
                count += 1
                if self.post_items(buffer, commit=commit, softCommit=softCommit):
                    # going good, clear them all
                    del buffer[:]
                else:
                    print('Solr posting failed. batch number=%d' % count)
                    return (num_docs, False)

            if (current_milli_time() - tt) > progress_delay:
                tt = current_milli_time()
                print("%d batches, %d docs " % (count, num_docs))

        res = True
        if len(buffer) > 0:
            res = self.post_items(buffer, commit=commit, softCommit=softCommit)
        return num_docs, res

    def get(self, doc_id, **kwargs):
        '''
            Gets a document given its id.
            returns None when item not found
        '''
        resp = self.query(query='id:"%s"' % doc_id, rows=1, **kwargs)
        if resp:
            if resp.get('response') and resp['response'].get('numFound', 0) > 0:
                return resp['response']['docs'][0]
        return None

    def commit(self):
        """
        Commit index
        """
        resp = requests.post(self.update_url + '?commit=true')
        if resp.status_code == 200:
            self.posted_items = 0
        return resp

    def query(self, query='*:*', start=0, rows=20, **kwargs):
        """
        Queries solr and returns results as a dictionary
        returns None on failure, items on success
        """
        payload = {
            'q': query,
            'wt': 'python',
            'start': start,
            'rows': rows
        }

        if kwargs:
            for key in kwargs:
                payload[key] = kwargs.get(key)

        resp = requests.get(self.query_url, params=payload)
        if resp.status_code == 200:
            return eval(resp.text)
        else:
            print(resp.status_code)
            return None

    def query_raw(self, query='*:*', start=0, rows=20, **kwargs):
        """
        Queries solr server and returns raw Solr resonse
        """
        payload = {
            'q': query,
            'wt': 'python',
            'start': start,
            'rows': rows
        }

        if kwargs:
            for key in kwargs:
                payload[key] = kwargs.get(key)

        return requests.get(self.query_url, params=payload)

    def query_iterator(self, query='*:*', start=0, rows=20, **kwargs):
        """
        Queries solr server and returns Solr response  as dictionary
        returns None on failure, iterator of results on success
        """
        payload = {
            'q': query,
            'wt': 'python',
            'rows': rows
        }

        if kwargs:
            for key in kwargs:
                payload[key] = kwargs.get(key)

        total = start + 1
        while start < total:
            payload['start'] = start
            print('start = %s, total= %s' % (start, total))
            resp = requests.get(self.query_url, params=payload)
            if not resp:
                print('no response from solr server!')
                break

            if resp.status_code == 200:
                resp = eval(resp.text)
                total = resp['response']['numFound']
                for doc in resp['response']['docs']:
                    start += 1
                    yield doc
            else:
                print(resp)
                print('Oops! Some thing went wrong while querying solr')
                print('Solr query params = %s', payload)
                break

    def __del__(self):
        """ commit pending docs before close """
        print('Solr: commit pending docs before close ...')
        print('Solr: status = ', self.commit())


if __name__ == '__main__':
    solr = Solr("http://localhost:8983/solr")
    docs = solr.query_iterator(fl="id")
    for doc in docs:
        print(doc)
    print('Done')
