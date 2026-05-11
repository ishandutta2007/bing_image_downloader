import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from io import BytesIO
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from bing_image_downloader.bing import Bing, _is_valid_image
from bing_image_downloader.downloader import download


def make_bing(query='cats', limit=5, output_dir=None, adult='off',
              timeout=60, filter='', verbose=False):
    if output_dir is None:
        output_dir = Path('/tmp/test_images')
    return Bing(query, limit, output_dir, adult, timeout, filter, verbose)


# ---------------------------------------------------------------------------
# Image validation (magic bytes)
# ---------------------------------------------------------------------------

class TestIsValidImage(unittest.TestCase):
    def test_jpeg(self):
        self.assertTrue(_is_valid_image(b'\xff\xd8\xff' + b'\x00' * 10))

    def test_png(self):
        self.assertTrue(_is_valid_image(b'\x89PNG\r\n\x1a\n' + b'\x00' * 10))

    def test_gif87(self):
        self.assertTrue(_is_valid_image(b'GIF87a' + b'\x00' * 10))

    def test_gif89(self):
        self.assertTrue(_is_valid_image(b'GIF89a' + b'\x00' * 10))

    def test_bmp(self):
        self.assertTrue(_is_valid_image(b'BM' + b'\x00' * 10))

    def test_webp(self):
        self.assertTrue(_is_valid_image(b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 10))

    def test_riff_non_webp_rejected(self):
        self.assertFalse(_is_valid_image(b'RIFF\x00\x00\x00\x00WAVE' + b'\x00' * 10))

    def test_tiff_little_endian(self):
        self.assertTrue(_is_valid_image(b'II\x2a\x00' + b'\x00' * 10))

    def test_tiff_big_endian(self):
        self.assertTrue(_is_valid_image(b'MM\x00\x2a' + b'\x00' * 10))

    def test_invalid_data(self):
        self.assertFalse(_is_valid_image(b'not an image'))

    def test_empty(self):
        self.assertFalse(_is_valid_image(b''))


# ---------------------------------------------------------------------------
# Bing.__init__
# ---------------------------------------------------------------------------

class TestBingInit(unittest.TestCase):
    def test_valid_init(self):
        b = make_bing(query='dogs', limit=10, timeout=30)
        self.assertEqual(b.query, 'dogs')
        self.assertEqual(b.limit, 10)
        self.assertEqual(b.timeout, 30)
        self.assertEqual(b.download_count, 0)
        self.assertEqual(b.page_counter, 0)

    def test_limit_must_be_int(self):
        with self.assertRaises(AssertionError):
            make_bing(limit='10')

    def test_timeout_must_be_int(self):
        with self.assertRaises(AssertionError):
            make_bing(timeout=60.0)


# ---------------------------------------------------------------------------
# Bing.get_filter
# ---------------------------------------------------------------------------

class TestGetFilter(unittest.TestCase):
    def setUp(self):
        self.bing = make_bing()

    def test_known_filters(self):
        cases = {
            'line': '+filterui:photo-linedrawing',
            'linedrawing': '+filterui:photo-linedrawing',
            'photo': '+filterui:photo-photo',
            'clipart': '+filterui:photo-clipart',
            'gif': '+filterui:photo-animatedgif',
            'animatedgif': '+filterui:photo-animatedgif',
            'transparent': '+filterui:photo-transparent',
        }
        for shorthand, expected in cases.items():
            with self.subTest(shorthand=shorthand):
                self.assertEqual(self.bing.get_filter(shorthand), expected)

    def test_unknown_filter_returns_empty(self):
        self.assertEqual(self.bing.get_filter('unknown'), '')
        self.assertEqual(self.bing.get_filter(''), '')


# ---------------------------------------------------------------------------
# Bing.save_image
# ---------------------------------------------------------------------------

class TestSaveImage(unittest.TestCase):
    VALID_PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_save_valid_image(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock(read=lambda: self.VALID_PNG)
        b = make_bing()
        with patch('builtins.open', mock_open()):
            b.save_image('http://example.com/img.png', Path('/tmp/img.png'))

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_save_invalid_image_raises(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock(read=lambda: b'not an image')
        b = make_bing()
        with self.assertRaises(ValueError):
            b.save_image('http://example.com/bad.jpg', Path('/tmp/bad.jpg'))


# ---------------------------------------------------------------------------
# Bing.download_image
# ---------------------------------------------------------------------------

class TestDownloadImage(unittest.TestCase):
    VALID_PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_success_increments_count(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock(read=lambda: self.VALID_PNG)
        b = make_bing()
        with patch('builtins.open', mock_open()):
            b.download_image('http://example.com/cat.jpg')
        self.assertEqual(b.download_count, 1)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_failure_does_not_increment(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('Network error')
        b = make_bing()
        b.download_image('http://example.com/fail.jpg')
        self.assertEqual(b.download_count, 0)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_unknown_extension_defaults_to_jpg(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock(read=lambda: self.VALID_PNG)
        b = make_bing()
        with patch('builtins.open', mock_open()):
            b.download_image('http://example.com/image.unknownext')
        self.assertEqual(b.download_count, 1)

    def test_spaces_in_url_are_encoded(self):
        # run() encodes spaces before calling download_image
        link = 'http://example.com/my image.jpg'
        self.assertEqual(link.replace(' ', '%20'), 'http://example.com/my%20image.jpg')


# ---------------------------------------------------------------------------
# Bing.run
# ---------------------------------------------------------------------------

class TestRun(unittest.TestCase):
    VALID_PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20

    def _page_html(self, urls):
        return ' '.join(f'murl&quot;:&quot;{u}&quot;' for u in urls).encode('utf8')

    def _mock_urlopen(self, mock_urlopen, img_urls):
        page_html = self._page_html(img_urls)

        def side_effect(request, timeout=None):
            resp = MagicMock()
            url = request.full_url if hasattr(request, 'full_url') else str(request)
            resp.read.return_value = page_html if 'bing.com' in url else self.VALID_PNG
            return resp

        mock_urlopen.side_effect = side_effect

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_stops_at_limit(self, mock_urlopen):
        self._mock_urlopen(mock_urlopen, [f'http://example.com/img{i}.jpg' for i in range(10)])
        b = make_bing(limit=3)
        with patch('builtins.open', mock_open()):
            b.run()
        self.assertEqual(b.download_count, 3)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_stops_on_empty_response(self, mock_urlopen):
        mock_urlopen.return_value = MagicMock(read=lambda: b'')
        b = make_bing(limit=10)
        b.run()
        self.assertEqual(b.download_count, 0)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_deduplicates_urls(self, mock_urlopen):
        # All same URL — downloads once, then no new images → stops
        self._mock_urlopen(mock_urlopen, ['http://example.com/same.jpg'] * 5)
        b = make_bing(limit=10)
        with patch('builtins.open', mock_open()):
            b.run()
        self.assertEqual(b.download_count, 1)


# ---------------------------------------------------------------------------
# downloader.download()
# ---------------------------------------------------------------------------

class TestDownloaderFunction(unittest.TestCase):
    @patch('bing_image_downloader.downloader.Bing')
    def test_adult_filter_off(self, MockBing):
        MockBing.return_value = MagicMock()
        with patch('bing_image_downloader.downloader.Path.is_dir', return_value=True):
            download('cats', limit=5, adult_filter_off=True, verbose=False)
        self.assertEqual(MockBing.call_args[0][3], 'off')

    @patch('bing_image_downloader.downloader.Bing')
    def test_adult_filter_on(self, MockBing):
        MockBing.return_value = MagicMock()
        with patch('bing_image_downloader.downloader.Path.is_dir', return_value=True):
            download('cats', limit=5, adult_filter_off=False, verbose=False)
        self.assertEqual(MockBing.call_args[0][3], 'on')

    @patch('bing_image_downloader.downloader.shutil.rmtree')
    @patch('bing_image_downloader.downloader.Bing')
    def test_force_replace_removes_dir(self, MockBing, mock_rmtree):
        MockBing.return_value = MagicMock()
        with patch('bing_image_downloader.downloader.Path.is_dir', return_value=True):
            download('cats', force_replace=True, verbose=False)
        mock_rmtree.assert_called_once()

    @patch('bing_image_downloader.downloader.shutil.rmtree')
    @patch('bing_image_downloader.downloader.Bing')
    def test_no_force_replace_keeps_dir(self, MockBing, mock_rmtree):
        MockBing.return_value = MagicMock()
        with patch('bing_image_downloader.downloader.Path.is_dir', return_value=True):
            download('cats', force_replace=False, verbose=False)
        mock_rmtree.assert_not_called()


# ---------------------------------------------------------------------------
# CLI (__main__)
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    @patch('bing_image_downloader.__main__.download')
    def test_basic_invocation(self, mock_dl):
        with patch('sys.argv', ['bing_image_downloader', 'cats']):
            from bing_image_downloader.__main__ import main
            main()
        mock_dl.assert_called_once()
        kwargs = mock_dl.call_args[1]
        self.assertEqual(kwargs['query'], 'cats')
        self.assertEqual(kwargs['limit'], 100)
        self.assertTrue(kwargs['adult_filter_off'])
        self.assertTrue(kwargs['verbose'])

    @patch('bing_image_downloader.__main__.download')
    def test_limit_flag(self, mock_dl):
        with patch('sys.argv', ['bing_image_downloader', 'dogs', '--limit', '25']):
            from bing_image_downloader.__main__ import main
            main()
        self.assertEqual(mock_dl.call_args[1]['limit'], 25)

    @patch('bing_image_downloader.__main__.download')
    def test_adult_filter_on_flag(self, mock_dl):
        with patch('sys.argv', ['bing_image_downloader', 'cats', '--adult-filter-on']):
            from bing_image_downloader.__main__ import main
            main()
        self.assertFalse(mock_dl.call_args[1]['adult_filter_off'])

    @patch('bing_image_downloader.__main__.download')
    def test_quiet_flag(self, mock_dl):
        with patch('sys.argv', ['bing_image_downloader', 'cats', '--quiet']):
            from bing_image_downloader.__main__ import main
            main()
        self.assertFalse(mock_dl.call_args[1]['verbose'])

    @patch('bing_image_downloader.__main__.download')
    def test_force_replace_flag(self, mock_dl):
        with patch('sys.argv', ['bing_image_downloader', 'cats', '--force-replace']):
            from bing_image_downloader.__main__ import main
            main()
        self.assertTrue(mock_dl.call_args[1]['force_replace'])

    @patch('bing_image_downloader.__main__.download')
    def test_filter_flag(self, mock_dl):
        with patch('sys.argv', ['bing_image_downloader', 'cats', '--filter', 'clipart']):
            from bing_image_downloader.__main__ import main
            main()
        self.assertEqual(mock_dl.call_args[1]['filter'], 'clipart')

    def test_invalid_filter_exits(self):
        with patch('sys.argv', ['bing_image_downloader', 'cats', '--filter', 'invalid']):
            from bing_image_downloader.__main__ import main
            with self.assertRaises(SystemExit):
                main()

    @patch('bing_image_downloader.__main__.download')
    def test_output_dir_flag(self, mock_dl):
        with patch('sys.argv', ['bing_image_downloader', 'cats', '--output-dir', '/tmp/imgs']):
            from bing_image_downloader.__main__ import main
            main()
        self.assertEqual(mock_dl.call_args[1]['output_dir'], '/tmp/imgs')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TestPublicApi(unittest.TestCase):
    def test_download_importable_from_package(self):
        from bing_image_downloader import download as dl
        self.assertTrue(callable(dl))


if __name__ == '__main__':
    unittest.main(verbosity=2)
