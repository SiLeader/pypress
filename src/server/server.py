import yaml
import json
import pickle
import pathlib
import sys
from http import server
from urllib import parse
import mimetypes

from generator.config import GeneratorConfig
from .config import ServerConfig
from generator.generator import n_gram


def main(_, directory):
    conf = ServerConfig(directory)
    gen_config = GeneratorConfig(directory)

    if conf.search.is_enabled:
        print('index: load')
        indexes_path = list(pathlib.Path(gen_config.generated_directory).glob('indexes.*'))
        if len(indexes_path) == 0:
            print('no index file in {}'.format(gen_config.generated_directory), file=sys.stderr)
            exit(1)

        indexes_path = indexes_path[0]
        if indexes_path.suffix not in ['.json', '.yml', '.pickle']:
            print('no matching index file in {}'.format(gen_config.generated_directory), file=sys.stderr)
            exit(2)

        loader = {
            '.json': json.load,
            '.yml': lambda __fp: yaml.load(__fp, Loader=yaml.SafeLoader),
            '.pickle': pickle.load,
        }[indexes_path.suffix]

        with indexes_path.open() as fp:
            indexes = loader(fp)
    else:
        print('index: skip')
        indexes = None

    if conf.content.is_enabled:
        print('content: prepare')
        content_root = pathlib.Path(gen_config.generated_contents_directory)
    else:
        print('content: skip')
        content_root = None

    class HttpRequestHandler(server.BaseHTTPRequestHandler):
        def __parse_url(self):
            path = parse.unquote(self.path, encoding='utf-8')
            path = parse.urlparse(path)
            return path.path, path.query

        def __handle_search(self, query: str):
            query = [q.split('=') for q in query.split('&')]
            query = {q[0]: q[1] for q in query}
            spl = sum([n_gram(q, gen_config.indexes.n) for q in query['q'].split('+')], [])

            pages_points = [indexes[_s] for _s in spl]  # List[List[Dict[str, Any]]]
            pages = {}
            for pp in pages_points:
                for p in pp:
                    pn = p['path']
                    if pn not in pages:
                        pages[pn] = 0
                    pages[pn] += p['point']

                first_time = False
            pages = [{'path': p[0], 'point': p[1]} for p in sorted(pages.items(), key=lambda x: x[1])]
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(pages).encode(encoding='utf-8'))

        def __handle_file(self, path):
            content = (content_root / path).resolve()
            if not str(content).startswith(str(content_root)):
                self.send_response_only(404)
                self.end_headers()
                return
            if not content.exists():
                self.send_response_only(404)
                self.end_headers()
                return

            self.send_response(200)
            mime, _ = mimetypes.guess_type(str(content))
            if mime is None:
                mime = 'application/octet-stream'

            mode = 'r'
            if mime.startswith('text/') or mime == 'application/json':
                mime += '; charset=utf-8'
            else:
                mode += 'b'
            with content.open(mode) as __fp:
                self.send_header('content-type', mime)
                self.end_headers()
                self.wfile.write(__fp.read().encode(encoding='utf-8'))

        def do_GET(self):
            path, query = self.__parse_url()
            if path == '/search':
                if indexes is None:
                    self.send_response_only(404)
                    return
                self.__handle_search(query)
            else:
                if content_root is None:
                    self.send_response_only(404)
                    return
                path = path.lstrip('/')
                self.__handle_file(path)

    with server.HTTPServer((conf.host, conf.port), HttpRequestHandler) as s:
        print('server: start on http://{}:{}'.format(conf.host, conf.port))
        s.serve_forever()
