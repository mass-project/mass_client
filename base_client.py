import threading
import time


class BaseClient(threading.Thread):

    def __init__(self, config_object):
        self._global_config = config_object['GLOBAL']
        self._local_config = config_object[self.__class__.__name__]
        self._should_terminate = False
        self._server_url = self._global_config['serverURL']
        self._base_url = self._server_url + self._global_config['APIEndpoint']
        self._sleep_time = int(self._global_config['SleepTime'])
        self._poll_time = int(self._local_config['PollTime'])
        self.api_key = self._global_config['api key']
        super(BaseClient, self).__init__()

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
