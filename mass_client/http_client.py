import json
import requests
import logging

logger = logging.getLogger('HTTPClient')
logger.setLevel(logging.INFO)


class APIKeyRejected(RuntimeError):
    pass


def _check_response_for_403(response, *args, **kwargs):
    if response.status_code == 403:
        raise APIKeyRejected('API Key was rejected {}'.format(response.content))


class HTTPClient():
    def __init__(self, api_key):
        self.default_header = {'content-type': 'application/json',
                               'Authorization': 'APIKEY {}'.format(api_key),
                               }
        self.defaul_hooks = {'response': _check_response_for_403}

    def post_json(self, url, data):
        r = requests.post(url, data=json.dumps(data), headers=self.default_header, hooks=self.defaul_hooks)
        return r

    def post_files(self, url, files):
        header = self.default_header.copy()
        header.pop('content-type')
        r = requests.post(url, files=files, headers=header)
        return r

    def get(self, url):
        r = requests.get(url, headers=self.default_header, hooks=self.defaul_hooks)
        return r

    def get_stream(self, url):
        r = requests.get(url, stream=True, headers=self.default_header, hooks=self.defaul_hooks)
        return r

    def delete(self, url):
        r = requests.delete(url, headers=self.default_header, hooks=self.defaul_hooks)
        return r

