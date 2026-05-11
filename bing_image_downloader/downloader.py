import sys
import re
import shutil
from pathlib import Path

try:
    from bing import Bing
except ImportError:
    from .bing import Bing


def download(query, limit=100, output_dir='dataset', adult_filter_off=True,
             force_replace=False, timeout=60, filter='', verbose=True):

    adult = 'off' if adult_filter_off else 'on'

    # Sanitize query for use as a folder name; keep the original query for the search
    safe_folder = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', query).strip('. ')
    image_dir = Path(output_dir).joinpath(safe_folder).absolute()

    if force_replace and Path.is_dir(image_dir):
        shutil.rmtree(image_dir)

    try:
        if not Path.is_dir(image_dir):
            Path.mkdir(image_dir, parents=True)
    except Exception as e:
        print('[Error] Failed to create directory.', e)
        sys.exit(1)

    print(f'[%] Downloading Images to {image_dir}')
    bing = Bing(query, limit, image_dir, adult, timeout, filter, verbose)
    bing.run()
