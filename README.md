![GitHub top language](https://img.shields.io/github/languages/top/gurugaurav/bing_image_downloader)
![GitHub](https://img.shields.io/github/license/gurugaurav/bing_image_downloader)
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Fgurugaurav%2Fbing_image_downloader&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false)](https://hits.seeyoufarm.com)

## Bing Image Downloader

Python library to download bulk images from Bing.com. No external dependencies — pure stdlib.

### Disclaimer

This program lets you download images from Bing. Please do not download or use any image that violates its copyright terms.

---

### Installation

```sh
pip install bing-image-downloader
```

Or from source:

```sh
git clone https://github.com/gurugaurav/bing_image_downloader
cd bing_image_downloader
pip install .
```

---

### Python API

```python
from bing_image_downloader import download

download(
    query,
    limit=100,
    output_dir='dataset',
    adult_filter_off=True,
    force_replace=False,
    timeout=60,
    filter='',
    verbose=True,
)
```

| Parameter | Default | Description |
|---|---|---|
| `query` | — | Search term |
| `limit` | `100` | Number of images to download |
| `output_dir` | `'dataset'` | Root directory; images go into `<output_dir>/<query>/` |
| `adult_filter_off` | `True` | Set `False` to enable Bing's adult content filter |
| `force_replace` | `False` | Delete existing output folder and start fresh |
| `timeout` | `60` | Request timeout in seconds |
| `filter` | `''` | Image type filter — see options below |
| `verbose` | `True` | Print download progress |

**Filter options:** `line`, `photo`, `clipart`, `gif`, `animatedgif`, `transparent`

---

### Command-line interface

```sh
python -m bing_image_downloader <query> [options]
```

```
positional arguments:
  query                 Search query

options:
  --limit N             Number of images to download (default: 100)
  --output-dir DIR      Root directory for downloads (default: dataset)
  --adult-filter-on     Enable adult content filter (default: off)
  --filter TYPE         Image type: line, photo, clipart, gif, animatedgif, transparent
  --timeout SECS        Request timeout in seconds (default: 60)
  --force-replace       Delete existing output directory before downloading
  --quiet               Suppress progress output
```

**Examples:**

```sh
# Download 50 cat images
python -m bing_image_downloader "cats" --limit 50

# Download clipart into a custom folder, silently
python -m bing_image_downloader "logo design" --limit 20 --output-dir ./images --filter clipart --quiet

# Fresh download with adult filter enabled
python -m bing_image_downloader "art" --force-replace --adult-filter-on
```

---

### Running tests

```sh
python test.py
```

---

### PyPI

https://pypi.org/project/bing-image-downloader/

---

### Donate

If this project was helpful, you can buy me a coffee.

[<img src="https://www.buymeacoffee.com/assets/img/guidelines/download-assets-sm-1.svg" alt="Buy Me A Coffee" width="180"/>](https://www.buymeacoffee.com/gurugaurav)
