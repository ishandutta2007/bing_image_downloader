import argparse
from .downloader import download

FILTER_CHOICES = ['line', 'photo', 'clipart', 'gif', 'animatedgif', 'transparent']


def main():
    parser = argparse.ArgumentParser(
        prog='bing_image_downloader',
        description='Download images from Bing image search.',
    )
    parser.add_argument('query', help='Search query')
    parser.add_argument('--limit', type=int, default=100, metavar='N',
                        help='Number of images to download (default: 100)')
    parser.add_argument('--output-dir', default='dataset', metavar='DIR',
                        help='Root directory for downloads (default: dataset)')
    parser.add_argument('--adult-filter-on', action='store_true',
                        help='Enable adult content filter (default: off)')
    parser.add_argument('--filter', choices=FILTER_CHOICES, default='', metavar='TYPE',
                        help='Image type filter: %(choices)s')
    parser.add_argument('--timeout', type=int, default=60, metavar='SECS',
                        help='Request timeout in seconds (default: 60)')
    parser.add_argument('--force-replace', action='store_true',
                        help='Delete existing output directory before downloading')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress progress output')

    args = parser.parse_args()

    download(
        query=args.query,
        limit=args.limit,
        output_dir=args.output_dir,
        adult_filter_off=not args.adult_filter_on,
        force_replace=args.force_replace,
        timeout=args.timeout,
        filter=args.filter,
        verbose=not args.quiet,
    )


if __name__ == '__main__':
    main()
