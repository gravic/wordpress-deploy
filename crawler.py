import os
import codecs
import shutil
from bs4 import BeautifulSoup
from htmlmin import minify
from urllib2 import urlopen, HTTPError
from datetime import datetime

OUTPUT_DIR = 'C:/Projects/Proof of Concept/crawler/dist/'
BASE_URL = 'http://gravictest2/remark'
PRODUCTION_URL = 'http://localhost:8080/test/remark'

completed = []
skipped = []

def crawl(url):
    print 'Crawling ' + url
    try:
        html = urlopen(url).read()
    except HTTPError, err:
        if err.code == 404:
            print '(404) Skipping ' + url
            skipped.append(url)
            return

    soup = BeautifulSoup(html)

    save(url, html)

    links = soup.find_all('a')

    for link in links:
        if not is_valid(link):
            continue
        if is_external(link['href']):
            continue
        if not is_html(link['href']):
            continue
        if link['href'] in completed or link['href'] in skipped:
            continue

        crawl(link['href'])

def crawl_css(url):
    print 'Crawling CSS resources...'

    try:
        html = urlopen(url).read()
    except HTTPError, err:
        if err.code == 404:
            print '(404) Skipping ' + url
            return

    soup = BeautifulSoup(html)

    links = soup.find_all('link')

    for link in links:
        try:
            if not 'http' in link['href']:
                continue

            content = urlopen(link['href']).read()
        except HTTPError, err:
            if err.code == 404:
                print '(404) Skipping ' + link['href']
                return

        output_path = to_path(link['href'])

        directory = os.path.dirname(output_path)

        if not os.path.exists(directory):
            os.makedirs(directory)

        print output_path

        with open(output_path, 'w+') as f:
            f.write(content)

def crawl_js(url):
    print 'Crawling JavaScript resources...'

    try:
        html = urlopen(url).read()
    except HTTPError, err:
        if err.code == 404:
            print '(404) Skipping ' + url
            return

    soup = BeautifulSoup(html)

    scripts = soup.find_all('script')

    for script in scripts:
        try:
            if not script.has_attr('src'):
                continue
            if not 'http' in script['src']:
                continue

            content = urlopen(script['src']).read()
        except HTTPError, err:
            if err.code == 404:
                print '(404) Skipping ' + script['src']
                return

        output_path = to_path(script['src'])

        directory = os.path.dirname(output_path)

        if not os.path.exists(directory):
            os.makedirs(directory)

        print output_path

        with open(output_path, 'w+') as f:
            f.write(content)

def is_valid(ele):
    if not ele.has_attr('href'):
        return False

    url = ele['href']

    return url not in ['', '#']

def is_external(url):
    return not url.startswith(BASE_URL)

def is_html(url):
    for substring in ['/wp-content/']:
        if substring in url:
            return False

    return True

def save(url, html):
    output_path = os.path.join(to_path(url), 'index.html')

    directory = os.path.dirname(output_path)

    if not os.path.exists(directory):
        os.makedirs(directory)

    minified_html = minify(unicode(html, 'utf-8', 'replace'), remove_comments=True, remove_empty_space=True, reduce_boolean_attributes=True, remove_optional_attribute_quotes=False)

    minified_html = replace_links(minified_html)

    with codecs.open(output_path, 'w+', encoding='utf-8') as f:
        f.write(minified_html)
        completed.append(url)

def to_path(url):
    path = os.path.join(OUTPUT_DIR, url.replace('http://gravictest2/', '')).replace('/', '\\')

    return path

def replace_links(html):
    return html.replace(BASE_URL, PRODUCTION_URL)

if __name__ == '__main__':
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

    start = datetime.now()
    crawl(BASE_URL)
    end = datetime.now()

    crawl_css(BASE_URL)
    crawl_js(BASE_URL)

    print 'Crawled {0} pages in {1}'.format(len(completed), end - start)
