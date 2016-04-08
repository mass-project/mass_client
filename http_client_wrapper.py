import json
import requests

DEFAULT_HEADERS = {'content-type': 'application/json'}


class HTTPClientWrapper():

    def post_json(url, post_data):
        r = requests.post(url, data=json.dumps(post_data), headers=DEFAULT_HEADERS)
        return r

    def get(url):
        r = requests.get(url, headers=DEFAULT_HEADERS)
        return r

    def get_stream(url):
        r = requests.get(url, stream=True, headers=DEFAULT_HEADERS)
        return r

    def delete(url):
        r = requests.delete(url, headers=DEFAULT_HEADERS)
        return r
