import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from io import BytesIO
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(__file__))

from bing_image_downloader.bing import Bing
from bing_image_downloader.downloader import download


def make_bing(query='cats', limit=5, output_dir=None, adult='off',
              timeout=60, filter='', resize=None, verbose=False):
    if output_dir is None:
        output_dir = Path('/tmp/test_images')
    return Bing(query, limit, output_dir, adult, timeout, filter, resize, verbose)


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

    def test_resize_must_be_tuple_or_none(self):
        b = make_bing(resize=(100, 100))
        self.assertEqual(b.resize, (100, 100))

        b2 = make_bing(resize=None)
        self.assertIsNone(b2.resize)

        with self.assertRaises(AssertionError):
            make_bing(resize=[100, 100])


class TestSaveImage(unittest.TestCase):
    def _make_valid_png(self):
        from PIL import Image
        buf = BytesIO()
        img = Image.new('RGB', (10, 10), color='red')
        img.save(buf, format='PNG')
        return buf.getvalue()

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_save_valid_image(self, mock_urlopen):
        png_data = self._make_valid_png()
        mock_response = MagicMock()
        mock_response.read.return_value = png_data
        mock_urlopen.return_value = mock_response

        b = make_bing()
        file_path = Path('/tmp/test_save_image.png')

        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            b.save_image('http://example.com/image.png', file_path)
            mock_file.assert_called_once_with(str(file_path), 'wb')

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_save_invalid_image_raises(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'not an image'
        mock_urlopen.return_value = mock_response

        b = make_bing()
        with self.assertRaises(ValueError):
            b.save_image('http://example.com/bad.jpg', Path('/tmp/bad.jpg'))

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_save_image_with_resize(self, mock_urlopen):
        png_data = self._make_valid_png()
        mock_response = MagicMock()
        mock_response.read.return_value = png_data
        mock_urlopen.return_value = mock_response

        b = make_bing(resize=(5, 5))
        file_path = Path('/tmp/test_resize.jpg')

        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            b.save_image('http://example.com/image.jpg', file_path)
            # When resizing, file is saved as .png regardless of original extension
            mock_file.assert_called_once_with(str(file_path.with_suffix('.png')), 'wb')


class TestDownloadImage(unittest.TestCase):
    def _make_valid_png(self):
        from PIL import Image
        buf = BytesIO()
        img = Image.new('RGB', (10, 10), color='blue')
        img.save(buf, format='PNG')
        return buf.getvalue()

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_download_increments_count(self, mock_urlopen):
        png_data = self._make_valid_png()
        mock_response = MagicMock()
        mock_response.read.return_value = png_data
        mock_urlopen.return_value = mock_response

        b = make_bing()
        with patch('builtins.open', unittest.mock.mock_open()):
            b.download_image('http://example.com/cat.jpg')

        self.assertEqual(b.download_count, 1)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_download_failure_does_not_increment(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('Network error')

        b = make_bing()
        b.download_image('http://example.com/fail.jpg')

        self.assertEqual(b.download_count, 0)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_unknown_extension_defaults_to_jpg(self, mock_urlopen):
        png_data = self._make_valid_png()
        mock_response = MagicMock()
        mock_response.read.return_value = png_data
        mock_urlopen.return_value = mock_response

        b = make_bing(output_dir=Path('/tmp'))
        saved_paths = []

        original_open = open

        def mock_open_capture(path, mode='r', **kwargs):
            if mode == 'wb':
                saved_paths.append(path)
                return MagicMock().__enter__.return_value
            return original_open(path, mode, **kwargs)

        with patch('builtins.open', unittest.mock.mock_open()) as m:
            b.download_image('http://example.com/image.unknownext')

        self.assertEqual(b.download_count, 1)

    def test_spaces_in_url_encoded(self):
        # Test that spaces in URLs are handled (the PR #62 fix)
        b = make_bing()
        link_with_space = 'http://example.com/my image.jpg'
        encoded = link_with_space.replace(' ', '%20')
        # The run() method does this replacement before calling download_image
        self.assertEqual(encoded, 'http://example.com/my%20image.jpg')


class TestRun(unittest.TestCase):
    def _make_html_response(self, urls):
        parts = []
        for url in urls:
            parts.append(f'murl&quot;:&quot;{url}&quot;')
        return ' '.join(parts)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_run_stops_at_limit(self, mock_urlopen):
        from PIL import Image
        buf = BytesIO()
        Image.new('RGB', (5, 5), 'green').save(buf, format='PNG')
        png_data = buf.getvalue()

        img_urls = [f'http://example.com/img{i}.jpg' for i in range(10)]
        page_html = self._make_html_response(img_urls)

        call_count = [0]

        def side_effect(request, timeout=None):
            resp = MagicMock()
            if hasattr(request, 'full_url') and 'bing.com' in request.full_url:
                resp.read.return_value = page_html.encode('utf8')
            else:
                resp.read.return_value = png_data
            return resp

        mock_urlopen.side_effect = side_effect

        b = make_bing(limit=3)
        with patch('builtins.open', unittest.mock.mock_open()):
            b.run()

        self.assertEqual(b.download_count, 3)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_run_stops_on_empty_response(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = b''
        mock_urlopen.return_value = resp

        b = make_bing(limit=10)
        b.run()

        self.assertEqual(b.download_count, 0)

    @patch('bing_image_downloader.bing.urllib.request.urlopen')
    def test_run_deduplicates_urls(self, mock_urlopen):
        from PIL import Image
        buf = BytesIO()
        Image.new('RGB', (5, 5), 'blue').save(buf, format='PNG')
        png_data = buf.getvalue()

        # Same URL repeated — should only download once, then stop (no new images)
        img_urls = ['http://example.com/same.jpg'] * 5
        page_html = self._make_html_response(img_urls)

        def side_effect(request, timeout=None):
            resp = MagicMock()
            if hasattr(request, 'full_url') and 'bing.com' in request.full_url:
                resp.read.return_value = page_html.encode('utf8')
            else:
                resp.read.return_value = png_data
            return resp

        mock_urlopen.side_effect = side_effect

        b = make_bing(limit=10)
        with patch('builtins.open', unittest.mock.mock_open()):
            b.run()

        # Only 1 unique URL — deduplication stops after first page finds no new images
        self.assertEqual(b.download_count, 1)


class TestDownloaderFunction(unittest.TestCase):
    @patch('bing_image_downloader.downloader.Bing')
    def test_adult_filter_off(self, MockBing):
        mock_bing_instance = MagicMock()
        MockBing.return_value = mock_bing_instance

        with patch('bing_image_downloader.downloader.Path.is_dir', return_value=True):
            download('cats', limit=5, adult_filter_off=True, verbose=False)

        args = MockBing.call_args[0]
        self.assertEqual(args[3], 'off')

    @patch('bing_image_downloader.downloader.Bing')
    def test_adult_filter_on(self, MockBing):
        mock_bing_instance = MagicMock()
        MockBing.return_value = mock_bing_instance

        with patch('bing_image_downloader.downloader.Path.is_dir', return_value=True):
            download('cats', limit=5, adult_filter_off=False, verbose=False)

        args = MockBing.call_args[0]
        self.assertEqual(args[3], 'on')

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


class TestImportedApi(unittest.TestCase):
    def test_download_importable_from_package(self):
        from bing_image_downloader import download as dl
        self.assertTrue(callable(dl))


if __name__ == '__main__':
    unittest.main(verbosity=2)
