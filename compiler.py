import os
import codecs
import shutil
import re
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

    def crawl_errors(self, errors):
        if not isinstance(errors, list):
            errors = [errors]

        for error in errors:
            url = os.path.join(self.testing_url, str(error))

            try:
                urlopen(url)
            except HTTPError, err:
                if err.code == error:
                    html = err.fp.read()
                    self.save(url, html)
                else:
                    self.skipped.append(url)

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

            urls = self.extract_urls(content)

            self.save_linked_contents(link['href'], urls)

            output_path = self.to_path(link['href'])

            directory = os.path.dirname(output_path)

            if not os.path.exists(directory):
                os.makedirs(directory)

            with open(output_path, 'w+') as f:
                f.write(content)
                self.completed_assets.append(url)

    def extract_urls(self, css):
        def unquote(url):
            if '\'' in url or '"' in url:
                return url[1:-1]

            return url

        urls = re.findall('url\(([^)]+)\)', css)

        return [unquote(url) for url in urls if 'data:' not in url]

    def save_linked_contents(self, parent, urls):
        for url in urls:
            parent_parts = parent.split('/')
            url_parts = url.split('/')

            for part in url_parts:
                if part == '.':
                    url_parts = url_parts[1:]
                    parent_parts = parent_parts[:-1]
                elif part == '..':
                    url_parts = url_parts[1:]
                    parent_parts = parent_parts[:-2]

            url = os.path.join('/'.join(parent_parts), '/'.join(url_parts))
            url = url.replace('\\', '/')

            if '?' in url:
                url = url[:url.index('?')]

            if '#' in url:
                url = url[:url.index('#')]

            content = urlopen(url).read()

            output_path = self.to_path(url)

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

    def crawl_xml(self, url):
        try:
            html = urlopen(url).read()
        except HTTPError, err:
            if err.code == 404:
                return

        soup = BeautifulSoup(html)

        output_path = self.to_path(url)

        directory = os.path.dirname(output_path)

        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(output_path, 'w+') as f:
            f.write(html)

        links = soup.find_all('loc')

        for link in links:
            href = link.get_text()

            if not self.is_xml(href):
                continue

            self.crawl_xml(href)

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

    def is_xml(self, url):
        return '.xml' in url

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
        self.crawl_errors(404)
        end = datetime.now()

        asset_start = datetime.now()
        self.crawl_css(self.testing_url)
        self.crawl_js(self.testing_url)
        self.crawl_php(os.path.join(self.theme_url, 'forms/'))
        asset_end = datetime.now()

        self.crawl_xml(os.path.join(self.testing_url, 'sitemap.xml'))

        print 'Crawled {0} pages in {1}'.format(len(self.completed), end - start)
        print 'Crawled {0} assets in {1}'.format(len(self.completed_assets), asset_end - asset_start)
