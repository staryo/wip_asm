from functools import partialmethod
from json import JSONDecodeError
from urllib.parse import urljoin

from requests import Session

from base.base import Base

__all__ = [
    'IAImportExport',
]

_DATETIME_SIMPLE_FORMAT = '%Y-%m-%dT%H:%M:%S'


class IAImportExport(Base):

    def __init__(self, login, password, base_url,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_url = base_url
        self._login = login
        self._password = password

        self._session = Session()
        self._session.verify = False

        self.cache = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()

    def _make_url(self, uri):
        return urljoin(self._base_url, uri)

    def get_from_rest_collection(self, table):
        if table not in self.cache:
            self._perform_login()
            self.cache[table] = self._perform_get(
                'rest/collection/{}'.format(table)
            )[table]
        return self.cache[table]

    def get_from_rest_collection_as_dict(self, table):
        return {
            row['id']:
                {
                    key: value for key, value in row.items()
                }
            for row in self.get_from_rest_collection(table)
        }

    def _perform_json_request(self, http_method, uri, **kwargs):
        url = self._make_url(uri)
        logger = self._logger

        logger.info('Выполнение {} запроса '
                    'по ссылке {!r}.'.format(http_method, url))

        logger.debug('Отправляемые данные: {!r}.'.format(kwargs))

        response = self._session.request(http_method,
                                         url=url,
                                         **kwargs)
        try:
            response_json = response.json()
        except JSONDecodeError:
            logger.error('Получен ответ на {} запрос по ссылке {!r}: '
                         '{!r}'.format(http_method, url, response))
            raise JSONDecodeError

        logger.debug('Получен ответ на {} запрос по ссылке {!r}: '
                     '{!r}'.format(http_method, url, response_json))
        return response_json

    _perform_get = partialmethod(_perform_json_request, 'GET')

    def _perform_post(self, uri, data):
        return self._perform_json_request('POST', uri, json=data)

    def _perform_put(self, uri, data):
        return self._perform_json_request('PUT', uri, json=data)

    def _perform_action(self, uri_part, **data):
        return self._perform_post(
            '/action/{}'.format(uri_part),
            data=data
        )

    def _perform_login(self):
        return self._perform_action(
            'login',
            data={
                'login': self._login,
                'password': self._password
            },
            action='login'
        )['data']

    @classmethod
    def from_config(cls, config):
        return cls(
            config['login'],
            config['password'],
            config['url'],
        )
