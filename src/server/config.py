import yaml
from generator.config import get_or_default


class SearchConfig:
    def __init__(self, data):
        self.__enabled = get_or_default(data, 'enabled', True)

    @property
    def is_enabled(self):
        return self.__enabled


class ContentConfig:
    def __init__(self, data):
        self.__enabled = get_or_default(data, 'enabled', True)

    @property
    def is_enabled(self):
        return self.__enabled


class ServerConfig:
    def __init__(self, directory: str):
        config_file = '{}/config/server.yml'.format(directory)

        data = None
        try:
            with open(config_file) as fp:
                data = yaml.load(fp, Loader=yaml.SafeLoader)
        except FileNotFoundError:
            print('{} is not found.'.format(config_file))
            print('using default configuration')

        if data is None:
            data = {}

        self.__search = SearchConfig(get_or_default(data, 'search', {}))
        self.__content = ContentConfig(get_or_default(data, 'content', {}))

        self.__host = get_or_default(data, 'host', 'localhost')
        self.__port = int(get_or_default(data, 'port', '8080'))

    @property
    def search(self):
        return self.__search

    @property
    def content(self):
        return self.__content

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port
