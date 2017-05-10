import requests
from lxml import etree
from time import sleep


def list_remote_files(remote_path, ext, start=0, num=100, delay=0.5, debug=False):
    remote_path = remote_path.replace("http://", "").replace("https://", "")
    base_url = "https://www.google.com/search?q=site:%s+filetype:%s&start=%d&num=%d"
    
    assert 0 < num <= 100
    assert 0 <= start
    
    total = start + 1
    while start < total:
        url = base_url % (remote_path, ext, start, num)
        if debug: print(url)
        resp = requests.get(url)
        assert resp.status_code == 200
        tree = etree.HTML(resp.text)
        remote_urls = tree.xpath("//cite/text()")
        stats = tree.xpath("//div[@id='resultStats']/text()")
        if stats:
            matched = re.match(pattern=".* ([0-9,]+) results.*",string=stats[0])
            total = int(matched.groups()[0].replace(",", ""))
        else:
            total =  start + len(remote_urls) 
        for u in filter(lambda x:x.startswith("http"), remote_urls):
            yield u

        start += num
        sleep(delay)
        if debug: print("Start = %d, total=%d" % (start, total))