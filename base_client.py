import threading
import time
import requests


class APIKeyRejected(RuntimeError):
    pass


def _check_response_for_403(response, *args, **kwargs):
    if response.status_code == 403:
        raise APIKeyRejected('API Key was rejected {}'.format(response.content))


class BaseClient(threading.Thread):

    def __init__(self, config_object):
        self._global_config = config_object['GLOBAL']
        self._local_config = config_object[self.__class__.__name__]
        self._should_terminate = False
        self._server_url = self._global_config['serverURL']
        self._base_url = self._server_url + self._global_config['APIEndpoint']
        self._sleep_time = int(self._global_config['SleepTime'])
        self._poll_time = int(self._local_config['PollTime'])
        self._init_request_session()
        super(BaseClient, self).__init__()

    def _init_request_session(self):
        self.mass_api_key = self._global_config['mass api key']
        if 'mass api key' in self._local_config:
            self.mass_api_key = self._local_config['mass api key']
        self.request_session = requests.Session()
        default_header = {'content-type': 'application/json',
                          'Accept': 'application/json',
                          'Authorization': 'APIKEY {}'.format(self.mass_api_key),
                          }
        self.request_session.headers.update(default_header)
        defaul_hooks = {'response': _check_response_for_403}
        self.request_session.hooks.update(defaul_hooks)

    def poll_server(self):
        raise NotImplementedError('This method needs to be implemented by a class derived from BaseClient')

    def stop(self):
        self._should_terminate = True

    def run(self):
        time_since_last_poll = 0
        do_poll = True
        while True:
            if self._should_terminate:
                return
            if do_poll is True:
                do_poll = self.poll_server()
            else:
                time.sleep(self._sleep_time)
                time_since_last_poll += self._sleep_time
                if time_since_last_poll >= self._poll_time:
                    do_poll = True
                    time_since_last_poll = 0
