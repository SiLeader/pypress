import yaml
import enum


def get_or_default(target, key, default=None):
    if key in target:
        return target[key]
    return default


class IndexType(enum.Enum):
    NGram = 'ngram'


class IndexFileType(enum.Enum):
    Pickle = 'pickle'
    Yaml = 'yaml'
    Json = 'json'


class IndexPointConfig:
    def __init__(self, data):
        self.__title = int(get_or_default(data, 'title', '2'))
        self.__content = int(get_or_default(data, 'content', '1'))

    @property
    def title(self):
        return self.__title

    @property
    def content(self):
        return self.__content


class IndexFileConfig:
    def __init__(self, data):
        self.__type = IndexFileType(get_or_default(data, 'type', 'yaml'))

    @property
    def type(self):
        return self.__type


class IndexConfig:
    def __init__(self, indexes):
        self.__enabled = get_or_default(indexes, 'enabled', True)
        self.__type = IndexType(get_or_default(indexes, 'type', IndexType.NGram.value))
        self.__n = int(get_or_default(indexes, 'n', '2'))
        self.__point = IndexPointConfig(get_or_default(indexes, 'point', {}))
        self.__file = IndexFileConfig(get_or_default(indexes, 'file', {}))

    @property
    def is_enabled(self):
        return self.__enabled

    @property
    def type(self):
        return self.__type

    @property
    def n(self):
        return self.__n

    @property
    def point(self):
        return self.__point

    @property
    def file(self):
        return self.__file


class GeneratorConfig:
    def __init__(self, directory: str):
        config_file = '{}/config/generator.yml'.format(directory)

        with open(config_file) as fp:
            data = yaml.load(fp, Loader=yaml.SafeLoader)

        if data is None:
            data = {}

        self.__indexes = IndexConfig(get_or_default(data, 'indexes', {}))
        self.__directory = directory
        self.__css = get_or_default(data, 'highlight', 'default')

    @property
    def indexes(self):
        return self.__indexes

    @property
    def directory(self):
        return self.__directory

    @property
    def generated_directory(self):
        return '{}/generated'.format(self.directory)

    @property
    def generated_contents_directory(self):
        return '{}/contents'.format(self.generated_directory)

    @property
    def temporary_directory(self):
        return '{}/temporary'.format(self.directory)

    @property
    def temporary_generated_directory(self):
        return '{}/generated'.format(self.temporary_directory)

    @property
    def temporary_generated_contents_directory(self):
        return '{}/contents'.format(self.temporary_generated_directory)

    @property
    def css(self) -> str:
        return self.__css
