import os
import codecs
import shutil
from bs4 import BeautifulSoup
from htmlmin import minify
from urllib2 import urlopen, HTTPError
from datetime import datetime

class Compiler(object):
    def __init__(self, output_dir, testing_url, production_url):
        self.output_dir = 'C:/Projects/Proof of Concept/crawler/dist/'
        self.testing_url = testing_url
        self.production_url = production_url

        self.completed = []
        self.skipped = []

    def crawl(self, url):
        print 'Crawling ' + url
        try:
            html = urlopen(url).read()
        except HTTPError, err:
            if err.code == 404:
                self.skipped.append(url)
                return

        soup = BeautifulSoup(html)

        self.save(url, html)

        links = soup.find_all('a')

        for link in links:
            if not self.is_valid(link):
                continue
            if self.is_external(link['href']):
                continue
            if not self.is_html(link['href']):
                continue
            if link['href'] in self.completed or link['href'] in self.skipped:
                continue

            self.crawl(link['href'])

    def is_valid(self, ele):
        if not ele.has_attr('href'):
            return False

        url = ele['href']

        return url not in ['', '#']

    def is_external(self, url):
        return not url.startswith(self.testing_url)

    def is_html(self, url):
        for substring in ['/wp-content/']:
            if substring in url:
                return False

        return True

    def save(self, url, html):
        output_path = os.path.join(self.to_path(url), 'index.html')

        directory = os.path.dirname(output_path)

        if not os.path.exists(directory):
            os.makedirs(directory)

        minified_html = minify(unicode(html, 'utf-8', 'replace'), remove_comments=True, remove_empty_space=True, reduce_boolean_attributes=True, remove_optional_attribute_quotes=False)

        minified_html = self.replace_links(minified_html)

        with codecs.open(output_path, 'w+', encoding='utf-8') as f:
            f.write(minified_html)
            self.completed.append(url)

    def to_path(self, url):
        path = os.path.join(self.output_dir, url.replace(self.testing_url, '')).replace('/', '\\')

        return path

    def replace_links(self, html):
        return html.replace(self.testing_url, self.production_url)

    def compile(self):
        print 'Compiling'

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

        start = datetime.now()
        self.crawl(self.testing_url)
        end = datetime.now()

        # self.crawl_css(BASE_URL)
        # self.crawl_js(BASE_URL)

        print 'Crawled {0} pages in {1}'.format(len(self.completed), end - start)
