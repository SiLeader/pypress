import pathlib
import shutil
import re
import sys
import typing
import json
import pickle

import yaml

from bs4 import BeautifulSoup

from concurrent.futures import ThreadPoolExecutor, Executor, ProcessPoolExecutor

import markdown
from jinja2 import Environment, FileSystemLoader, Template

from .config import GeneratorConfig, IndexConfig, get_or_default, IndexFileType


def main(_, directory):
    conf = GeneratorConfig(directory)
    environment = Environment(loader=FileSystemLoader(conf.directory, encoding='utf-8'))
    template = environment.get_template('page/frame.html')

    shutil.rmtree(conf.temporary_directory, ignore_errors=True)
    pathlib.Path(conf.temporary_generated_directory).mkdir(parents=True, exist_ok=True)
    pathlib.Path(conf.temporary_generated_contents_directory).mkdir(parents=True, exist_ok=True)

    print('generate')
    ptcs = convert_files(conf, template)
    generate_style_file(conf)

    print('indexing')
    generate_indexes(conf, ptcs)

    print('replace')
    print('  remove: {}'.format(conf.generated_directory))
    shutil.rmtree(conf.generated_directory, ignore_errors=True)
    print('  copy: {} -> {}'.format(conf.temporary_generated_directory, conf.generated_directory))
    shutil.copytree(conf.temporary_generated_directory, conf.generated_directory)


def n_gram(target, n):
    return [target[idx:idx + n] for idx in range(len(target) - n + 1)]


def __generate_index(
        conf: IndexConfig,
        path: str,
        title: str, content: str) -> typing.Dict[str, typing.Tuple[int, str]]:
    print('  index: {}'.format(path))
    soup = BeautifulSoup(content, 'html.parser')
    for script in soup(['script', 'style']):
        script.decompose()

    text = soup.get_text()
    lines = [l.strip() for l in text.splitlines()]
    text = ''.join([l for l in lines if l])

    content_ng = n_gram(text, conf.n)
    title_ng = n_gram(title, conf.n)

    def calculate_point(ng: typing.List[str], point_per_content):
        __point = {}
        for n in ng:
            if n not in __point:
                __point[n] = 0
            __point[n] += point_per_content
        return __point

    content_point = calculate_point(content_ng, conf.point.content)
    title_point = calculate_point(title_ng, conf.point.title)

    keys = set(content_point.keys())
    keys.update(title_point.keys())

    index = {}
    for key in keys:
        point = get_or_default(content_point, key, 0) + get_or_default(title_point, key, 0)
        index[key] = point, path

    return index


def __generate_index_impl(cptc):
    conf = cptc[0]
    ptc = cptc[1]
    return __generate_index(conf, ptc[0], ptc[1], ptc[2])


def generate_indexes(conf: GeneratorConfig, ptcs: typing.List[typing.Dict[str, typing.Tuple[int, str]]]):
    if not conf.indexes.is_enabled:
        print('  skipped')
        return

    with ProcessPoolExecutor() as executor:
        indexes = [
            i for i in executor.map(
                __generate_index_impl,
                [(conf.indexes, ptc) for ptc in ptcs]
            )
        ]
    keys = set()
    for v in indexes:
        keys.update(v.keys())

    i = {}  # Dict[str, List[Tuple[int, str]]]
    for key in keys:
        if key not in i:
            i[key] = []
        for v in indexes:
            if key not in v:
                continue
            i[key].append(v[key])

    indexes = {}
    for k, v in i.items():
        indexes[k] = [{'point': p, 'path': v} for p, v in sorted(v, key=lambda x: x[0])]

    file_type = conf.indexes.file.type
    file_name = {
        IndexFileType.Json: '/indexes.json',
        IndexFileType.Yaml: '/indexes.yml',
        IndexFileType.Pickle: '/indexes.pickle',
    }[file_type]

    output_func = {
        IndexFileType.Json: lambda __fp: json.dump(indexes, __fp, sort_keys=True, indent=2),
        IndexFileType.Yaml: lambda __fp: yaml.dump(indexes, __fp, allow_unicode=True, Dumper=yaml.SafeDumper),
        IndexFileType.Pickle: lambda __fp: pickle.dump(indexes, __fp),
    }

    with open(conf.temporary_generated_directory + file_name, 'w') as fp:
        output_func[file_type](fp)


__COMMENT_REGEX = re.compile(r'<!--((.|\s)+)-->')


def __convert_markdown_file(
        conf: GeneratorConfig, template: Template,
        markdown_file: str, output_file: pathlib.Path) -> typing.Tuple[str, str, str]:
    with open(markdown_file) as fp:
        content = fp.read()

    comment = __COMMENT_REGEX.search(content, endpos=100)
    if comment is not None:
        comment = comment.group(1)
        comment = [l.split(':') for l in comment.strip().splitlines(keepends=False)]
        comment = {l[0].strip(): l[1].strip() for l in comment}
    else:
        comment = {}

    if 'title' in comment:
        title = comment['title']
    else:
        title = pathlib.Path(markdown_file).stem

    md_html = markdown.markdown(content, extensions=['gfm', 'extra'])

    with output_file.open('w') as fp:
        html = template.render(
            content=md_html,
            title=title,
            css='<link rel="stylesheet" type="text/css" href="{}.css">'.format(conf.css)
        )
        fp.write(html)
    output_file = output_file.relative_to(pathlib.Path(conf.temporary_generated_contents_directory))
    return str(output_file), title, md_html


def convert_file(
        conf: GeneratorConfig,
        executor: Executor, template: Template, file: str) -> typing.Optional[typing.Tuple[str, str, str]]:
    file = pathlib.Path(file)
    output_file = pathlib.Path('{}/{}'.format(conf.temporary_generated_contents_directory, file))

    if file.is_dir():
        print('  mkdir: {}'.format(file))
        output_file.mkdir(parents=True, exist_ok=True)
        executor.map(lambda f: convert_file(conf, executor, template, str(f)), output_file.glob('*'))
        return None

    file_ext = file.suffix
    if file_ext in ['.md', '.markdown']:
        print('  markdown: {}'.format(file))
        output_file = pathlib.Path('{}/{}.html'.format(conf.temporary_generated_contents_directory, file.stem))
        return __convert_markdown_file(conf, template, str(file), output_file)

    print('  copy: {}'.format(file))
    shutil.copy(str(file), str(output_file))
    return None


def convert_files(conf: GeneratorConfig, template: Template):
    file = pathlib.Path(conf.directory)

    with ThreadPoolExecutor() as executor:
        ptcs = [
            optc for optc in executor.map(
                lambda f: convert_file(conf, executor, template, str(f)),
                (file / 'page/contents').glob('*')
            )
            if optc is not None
        ]
    return ptcs


def generate_style_file(conf: GeneratorConfig):
    style_sheet = conf.css
    print('  css: {}'.format(style_sheet))
    output_file = pathlib.Path('{}/{}.css'.format(conf.temporary_generated_contents_directory, style_sheet))

    css_dir = pathlib.Path(__file__).parent / 'builtin/css'

    supporting_css_files = css_dir.glob('*.css')
    supporting_css = {f.stem: str(f) for f in supporting_css_files}
    if style_sheet not in supporting_css:
        print('style sheet {} is not found.'.format(style_sheet), file=sys.stderr)
        print('supporting style sheet names:', file=sys.stderr)

        css = []
        supporting_css = list(supporting_css.values())
        for i in range(len(supporting_css)):
            css.append(supporting_css[i])
            if i % 5 == 0:
                print(', '.join(css), file=sys.stderr)
                css.clear()
            print(', '.join(css), file=sys.stderr)

        exit(1)

    shutil.copy(supporting_css[style_sheet], str(output_file))
