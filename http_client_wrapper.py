import json
import requests
import logging

logger = logging.getLogger('HTTPClientWrapper')
logger.setLevel(logging.INFO)

DEFAULT_HEADERS = {'content-type': 'application/json'}


class APIKeyRejected(RuntimeError):
    pass


def _check_response_for_403(response, key):
    if response.status_code == 403:
        logger.warn('API Key was rejected! Key: {}')
        raise APIKeyRejected()


def _add_api_key(header, api_key):
    header['X-API-KEY'] = api_key
    logger.info('HEADER: {}'.format(header))

class HTTPClientWrapper():

    def post_json(url, post_data, api_key):
        _add_api_key(DEFAULT_HEADERS, api_key)
        r = requests.post(url, data=json.dumps(post_data), headers=DEFAULT_HEADERS)
        _check_response_for_403(r, api_key)
        return r

    def get(url, api_key):
        _add_api_key(DEFAULT_HEADERS, api_key)
        r = requests.get(url, headers=DEFAULT_HEADERS)
        _check_response_for_403(r, api_key)
        return r

    def get_stream(url, api_key):
        _add_api_key(DEFAULT_HEADERS, api_key)
        r = requests.get(url, stream=True, headers=DEFAULT_HEADERS)
        _check_response_for_403(r, api_key)
        return r

    def delete(url, api_key):
        _add_api_key(DEFAULT_HEADERS, api_key)
        r = requests.delete(url, headers=DEFAULT_HEADERS)
        _check_response_for_403(r, api_key)
        return r
