import re
import json
# 3rd party packages
import requests
from bs4 import BeautifulSoup
#
import csv
from multiprocessing import Pool
import time

# logo may come as words logo, brand and ??

# case 1 : Search all images with img tag:
#         a) url with 'logo'
#         b) class, id, attribute with 'logo'
# case 2 : Search all images with svg tag:
#         a) class, id, attribute with 'logo'
# TODO: if not found any, search for word as the name of the site


class LogoCrawler:
    def __init__(self, path_to_csv):
        self.urls = self.read_urls_to_list(path_to_csv)
        self.favicon_url = " "
        self.logo_url = " "
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
            "Upgrade-Insecure-Requests": "1", "DNT": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate"}
        self.encoded_svg = None

    @staticmethod
    def read_urls_to_list(path):
        urls = []
        with open(path, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
            for row in reader:
                urls.append('http://www.' + row[0])
            return urls

    def encode_svg(self, site_url, svg_tag):
        # Implement encoding
        self.encoded_svg = {site_url: str(svg_tag)}

    def search_for_logo(self, soup, search_pattern, site_url):
        found_the_logo = False
        # CASE 1
        # all images with img tag
        img_tags = soup.find_all('img', alt=True)
        # case a, search within the URL of images for words : {search_pattern}
        try:
            img_urls = [img['src'] for img in img_tags]
        except Exception:
            img_urls = []
        for url in img_urls:
            filename = re.search(search_pattern, url)
            if not filename:
                continue
            if 'http' not in url:
                url = '{}{}'.format(site_url, url)
            self.logo_url = url
            found_the_logo = True
        # case b
        if not found_the_logo:
            for img_tag in img_tags:
                try:
                    class_name = ''.join(img_tag.get('class'))
                    if re.search(search_pattern, class_name):
                        self.logo_url = img_tag['src']
                        found_the_logo = True
                except Exception:
                    pass
                try:
                    id_name = ''.join(img_tag.get('id'))
                    if re.search(search_pattern, id_name):
                        self.logo_url = img_tag['src']
                        found_the_logo = True
                except Exception:
                    pass
                try:
                    logo_url_by_alt = img_tag.get('alt')
                    if re.search(search_pattern, logo_url_by_alt):
                        self.logo_url = img_tag['src']
                        found_the_logo = True
                except Exception:
                    pass

        # CASE 2
        if not found_the_logo:
            svg_tags = soup.find_all('svg')
            if len(svg_tags) > 1:
                for svg_tag in svg_tags:
                    # Search for parent with class or id with RE (search pattern), if found we assume that it is a logo
                    parent_tags_by_class = svg_tag.find_parent(attrs={"class": search_pattern})
                    parent_tags_by_id = svg_tag.find_parent(attrs={"id": search_pattern})
                    if parent_tags_by_class or parent_tags_by_id:
                        self.encode_svg(site_url, svg_tag)
                        self.logo_url = site_url
            elif len(svg_tags) == 1:
                # if only one svg and we did not find any logo using img tag, we assume that this svg is a logo
                self.encode_svg(site_url, svg_tags[0])
                self.logo_url = site_url
            else:
                logo_url = 'Not Found'
                self.logo_url = logo_url
        return self.logo_url

    def run_logo_crawler(self, site_url):
        self.encoded_svg = None
        try:
            response = requests.get(site_url, stream=True, headers=self.headers, timeout=15)
        except Exception:
            return site_url, 'Site Not Opened', self.encoded_svg

        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            search_pattern = re.compile(r'logo|brand', re.IGNORECASE)
            logo_url = self.search_for_logo(soup, search_pattern, site_url)
            # If we did not find anything, we can look for search pattern with the url itself
            if logo_url in ['Not Found']:
                cleaned_url = site_url.split('.')[-2]
                search_pattern = re.compile(r'{}'.format(cleaned_url), re.IGNORECASE)
                logo_url = self.search_for_logo(soup, search_pattern, site_url)
            return site_url, logo_url, self.encoded_svg
        except Exception:
            return site_url, 'Soap Not loaded', self.encoded_svg


def write_to_csv(csv_name, content):
    fp = open('encoded_svgs.json', 'w')
    with open(csv_name, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', dialect='excel')
        for row in content:
            csv_writer.writerow(row[0:2])
            if row[2]:
                json.dump(row[2], fp)
                fp.write('\n')
    fp.close()


if __name__ == '__main__':
    path = '../../websites.csv'
    print('Started running')
    crawler = LogoCrawler(path)
    start_time = time.time()
    p = Pool(20)
    results = p.map(crawler.run_logo_crawler, crawler.urls, chunksize=20)
    p.terminate()
    p.join()

    write_to_csv('out.csv', results)
    print('elapsed_time', time.time() - start_time)
