import argparse
import pathlib

from generator import generator
from server import server


def main():
    parser = argparse.ArgumentParser()

    cwd = str(pathlib.Path.cwd())
    parser.add_argument('--directory', '-d', help='base directory (default: {})'.format(cwd), default=cwd)

    sub = parser.add_subparsers()

    gen = sub.add_parser('generate')
    gen.set_defaults(handler=generator.main)

    svr = sub.add_parser('server')
    svr.add_argument('--search', help='enable search api', action='store_true')
    svr.add_argument('--content', help='enable content server', action='store_true')
    svr.set_defaults(handler=server.main)

    args = parser.parse_args()

    if hasattr(args, 'handler'):
        args.handler(args, args.directory)
    else:
        parser.print_usage()


if __name__ == '__main__':
    main()
