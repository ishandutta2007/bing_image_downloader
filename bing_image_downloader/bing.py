from pathlib import Path
import urllib.request
import urllib.parse
import posixpath
import html as _html
import re

'''
Python api to download image form Bing.
Author: Guru Prasad (g.gaurav541@gmail.com)
'''

# Magic bytes for common image formats
_IMAGE_MAGIC = [
    b'\xff\xd8\xff',        # JPEG
    b'\x89PNG\r\n\x1a\n',  # PNG
    b'GIF87a', b'GIF89a',  # GIF
    b'BM',                  # BMP
    b'II\x2a\x00', b'MM\x00\x2a',  # TIFF
]


def _is_valid_image(data):
    for magic in _IMAGE_MAGIC:
        if data.startswith(magic):
            return True
    # WEBP: RIFF????WEBP
    return len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP'


class Bing:
    def __init__(self, query, limit, output_dir, adult, timeout, filter='', verbose=True):
        self.download_count = 0
        self.query = query
        self.output_dir = output_dir
        self.adult = adult
        self.filter = filter
        self.verbose = verbose
        self.seen = set()
        self.page_counter = 0

        assert isinstance(limit, int), "limit must be integer"
        self.limit = limit
        assert isinstance(timeout, int), "timeout must be integer"
        self.timeout = timeout

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive',
        }

    def get_filter(self, shorthand):
        filters = {
            'line': '+filterui:photo-linedrawing',
            'linedrawing': '+filterui:photo-linedrawing',
            'photo': '+filterui:photo-photo',
            'clipart': '+filterui:photo-clipart',
            'gif': '+filterui:photo-animatedgif',
            'animatedgif': '+filterui:photo-animatedgif',
            'transparent': '+filterui:photo-transparent',
        }
        return filters.get(shorthand, '')

    def save_image(self, link, file_path):
        # Re-encode URL to handle non-ASCII characters (e.g. accented chars in path)
        parsed = urllib.parse.urlsplit(link)
        safe_link = urllib.parse.urlunsplit((
            parsed.scheme,
            parsed.netloc,
            urllib.parse.quote(parsed.path, safe='/:@!$&\'()*+,;='),
            urllib.parse.quote(parsed.query, safe='=&+%:@!$\'()*,;'),
            parsed.fragment,
        ))
        request = urllib.request.Request(safe_link, None, self.headers)
        data = urllib.request.urlopen(request, timeout=self.timeout).read()
        if not _is_valid_image(data):
            raise ValueError(f'Invalid image, not saving {link}')
        with open(str(file_path), 'wb') as f:
            f.write(data)

    def download_image(self, link):
        self.download_count += 1
        try:
            path = urllib.parse.urlsplit(link).path
            filename = posixpath.basename(path).split('?')[0]
            file_type = filename.split('.')[-1].lower()
            if file_type not in {'jpe', 'jpeg', 'jfif', 'exif', 'tiff', 'gif', 'bmp', 'png', 'webp', 'jpg'}:
                file_type = 'jpg'

            if self.verbose:
                print(f'[%] Downloading Image #{self.download_count} from {link}')

            self.save_image(link, self.output_dir / f'Image_{self.download_count}.{file_type}')

            if self.verbose:
                print('[%] File Downloaded!\n')
        except Exception as e:
            self.download_count -= 1
            print(f'[!] Issue getting: {link}\n[!] Error:: {e}')

    def run(self):
        while self.download_count < self.limit:
            if self.verbose:
                print(f'\n\n[!!] Indexing page: {self.page_counter + 1}\n')

            params = urllib.parse.urlencode({
                'q': self.query,
                'first': self.page_counter,
                'count': self.limit,
                'adlt': self.adult,
                'qft': self.get_filter(self.filter or ''),
            })
            request_url = 'https://www.bing.com/images/async?' + params
            request = urllib.request.Request(request_url, None, headers=self.headers)
            response = urllib.request.urlopen(request, timeout=self.timeout)
            html = response.read().decode('utf8')

            if html == '':
                print('[%] No more images are available')
                break

            # Unescape HTML entities in extracted URLs (e.g. &amp; → &) before encoding
            links = re.findall('murl&quot;:&quot;(.*?)&quot;', html)
            links = [_html.unescape(link).replace(' ', '%20') for link in links]

            if self.verbose:
                print(f'[%] Indexed {len(links)} Images on Page {self.page_counter + 1}.')
                print('\n===============================================\n')

            prev_count = self.download_count
            for link in links:
                if self.download_count < self.limit and link not in self.seen:
                    self.seen.add(link)
                    self.download_image(link)

            if self.download_count == prev_count:
                print('[%] No new images found, stopping.')
                break

            self.page_counter += 1

        print(f'\n\n[%] Done. Downloaded {self.download_count} images.')
