import os
import codecs
import shutil
from bs4 import BeautifulSoup
from htmlmin import minify
from urllib2 import urlopen, HTTPError
from datetime import datetime

class Compiler(object):
    def __init__(self, output_dir, testing_url, production_url, theme_url):
        self.output_dir = os.path.abspath(output_dir)
        self.testing_url = testing_url
        self.production_url = production_url if production_url[-1] == '/' else production_url + '/'
        self.theme_url = theme_url

        self.completed = []
        self.skipped = []
        self.completed_assets = []
        self.skipped_assets = []

    def crawl(self, url):
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

    def crawl_css(self, url):
        try:
            html = urlopen(url).read()
        except HTTPError, err:
            if err.code == 404:
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
                    return

            output_path = self.to_path(link['href'])

            directory = os.path.dirname(output_path)

            if not os.path.exists(directory):
                os.makedirs(directory)

            with open(output_path, 'w+') as f:
                f.write(content)
                self.completed_assets.append(url)

    def crawl_js(self, url):
        try:
            html = urlopen(url).read()
        except HTTPError, err:
            if err.code == 404:
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
                    return

            output_path = self.to_path(script['src'])

            directory = os.path.dirname(output_path)

            if not os.path.exists(directory):
                os.makedirs(directory)

            with open(output_path, 'w+') as f:
                f.write(content)
                self.completed_assets.append(url)

    def crawl_php(self, url):
        try:
            html = urlopen(url).read()
        except HTTPError, err:
            if err.code == 404:
                return

        soup = BeautifulSoup(html)

        links = soup.find_all('a')

        skip = ['Name', 'Last modified', 'Size', 'Description', 'Parent Directory']

        for link in links:
            if link.text in skip:
                continue

            if link.text[-1:] == '/':
                self.crawl_php(os.path.join(url, link['href']))
            else:
                try:
                    content = urlopen(os.path.join(url, link['href'])).read()
                except HTTPError, err:
                    if err.code == 404:
                        pass

                output_path = os.path.join(self.to_path(url), link['href'])

                directory = os.path.dirname(output_path)

                if not os.path.exists(directory):
                    os.makedirs(directory)

                with open(output_path, 'w+') as f:
                    f.write(content)
                    self.completed_assets.append(url)

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
        path = os.path.abspath(os.path.join(self.output_dir, url.replace(self.testing_url, '')))

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

        asset_start = datetime.now()
        self.crawl_css(self.testing_url)
        self.crawl_js(self.testing_url)
        self.crawl_php(os.path.join(self.theme_url, 'forms/'))
        asset_end = datetime.now()

        print 'Crawled {0} pages in {1}'.format(len(self.completed), end - start)
        print 'Crawled {0} assets in {1}'.format(len(self.completed_assets), asset_end - asset_start)

if __name__ == '__main__':
    compiler = Compiler('./test/', 'http://gravictest2/remark/', 'http://remarksoftware.com', 'http://gravictest2/remark/wp-content/themes/remark/')

    compiler.compile()
