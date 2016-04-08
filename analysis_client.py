import re
from .http_client_wrapper import HTTPClientWrapper
from requests.exceptions import ConnectionError
import logging
import json
from tempfile import NamedTemporaryFile
from os import chmod
from .base_client import BaseClient
from contextlib import contextmanager
import requests
import datetime

# Log configuration
logger = logging.getLogger('mass_client_manager')
logger.setLevel(logging.INFO)

def download_sample_to_file(sample_url, file):
    r = HTTPClientWrapper.get_stream(sample_url + 'download/')
    for block in r.iter_content(1024):
        if not block:
            break
        file.write(block)

def get_sample_dict(analysis_request):
    sample_url = analysis_request['sample']
    return requests.get(sample_url).json()

@contextmanager
def temporary_sample_file(sample_dict):
    file = NamedTemporaryFile()
    chmod(file.name, 0o666)
    download_sample_to_file(sample_dict['url'], file)
    file.flush()
    yield file.name
    file.close()

class AnalysisClient(BaseClient):
    def __init__(self, config_object):
        super(AnalysisClient, self).__init__(config_object)
        self._instance_uuid = self._local_config['UUID']
        self._analysis_system_name = self._local_config['SystemName']
        self._analyses_in_progress = list()
        self._check_registration()

    def _get_analysis_system_reference_url(self):
        return self._base_url + 'analysis_system/' + self._analysis_system_name + '/'

    def _register(self):
        registration_data = {
            'analysis_system': self._get_analysis_system_reference_url(),
            'uuid': self._instance_uuid
        }
        response = HTTPClientWrapper.post_json(self._base_url + 'analysis_system_instance/', registration_data)

        if response.status_code != 201:
            logger.warn('Registration response: %s', response.text)
            return False
        else:
            return True

    def _is_registered(self):
        response = HTTPClientWrapper.get(self._base_url + 'analysis_system_instance/' + self._instance_uuid + '/')
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            return False
            # Maybe we should throw an error message here, since something is really going wrong

    def _check_registration(self):
        # Check if this system is already registered with the MASS server. If not, try registering
        if self._is_registered():
            logger.info('Analysis system instance is already registered with the MASS server.')
        else:
            logger.info('Analysis system instance not registered with the MASS server. Trying to register it now...')
            register_result = self._register()
            if register_result is False:
                logger.error('Registration with the MASS server failed.')
                raise RuntimeError('Registration failed.')
            else:
                logger.info('Analysis system successfully registered with MASS server.')

    def submit_report(self, analysis_url, report_data, status_code=0):
        report_data['status'] = status_code
        self._analyses_in_progress.remove(analysis_url)
        response = HTTPClientWrapper.post_json(analysis_url + 'submit_report/', report_data)

        if response.status_code != 204:
            logger.warn('Creating report failed: %s', response.text)
            return False
        else:
            return True

    def _handover_scheduled_analysis_to_application(self, analysis_url):
        self._analyses_in_progress.append(analysis_url)
        response = HTTPClientWrapper.get(analysis_url)

        # First check if the response was received correctly
        if response.status_code != 200:
            logger.warn('Getting information about scheduled analysis failed: %s', response.text)
            return

        # Check if the UUID is equal to our UUID
        json_response = json.loads(response.text)
        uuid = re.search('/analysis_system_instance/([a-z0-9\-]+)/', json_response['analysis_system_instance'])
        if uuid.group(1) != self._instance_uuid:
            logger.warn('Not processing analysis request which is scheduled for a different UUID: %s', uuid.group(1))
            return

        logger.info('Analyzing sample %s on system %s UUID %s', json_response['sample'], self._analysis_system_name, self._instance_uuid)
        self.analyze(json_response)

    def analyze(self, analysis_request):
        raise NotImplementedError('This method needs to be implemented by a class derived from AnalysisClient')

    def poll_server(self):
        try:
            logger.info('Polling for scheduled analysis.')

            # Get analysis list
            response = HTTPClientWrapper.get(self._base_url + 'analysis_system_instance/' + self._instance_uuid + '/scheduled_analyses/')
            if response.status_code != 200:
                logger.warn('Polling for scheduled analysis failed: %s', response.text)
                return False

            # See if there is something to do
            processed_analyses = 0
            analysis_list = json.loads(response.text)
            for analysis in analysis_list['results']:
                if self._should_terminate is True:
                    return True
                # If this analysis is already in progress, skip it
                if analysis['url'] in self._analyses_in_progress:
                    continue
                # Do the analysis
                self._handover_scheduled_analysis_to_application(analysis['url'])
                processed_analyses += 1
        except ConnectionError:
            logger.error('MASS server not reachable. Trying again ...')


    def send_error_report(self, data, msg):
        report = {'status_message': msg}
        self.submit_report(data['url'], report, status_code=1)
        return


class FileAnalysisClient(AnalysisClient):
    def __init__(self, config_object):
        super(FileAnalysisClient, self).__init__(config_object)

    def analyze(self, analysis_request):
        if 'sample' in analysis_request :
            self.sample_dict = get_sample_dict(analysis_request)
            if self.sample_dict['_cls'].startswith('Sample.FileSample'):
                self.do_analysis(analysis_request)
            else:
                msg = 'ERROR - No file found to scan.'
                self.send_error_report(analysis_request, msg)

    def do_analysis(self, analysis_request):
        raise NotImplementedError('You need to inherit from this class and implement this method.')


class DomainAnalysisClient(AnalysisClient):
    def __init__(self, config_object):
        super(DomainAnalysisClient, self).__init__(config_object)

    def analyze(self, analysis_request):
        if 'sample' in analysis_request :
            self.sample_dict = get_sample_dict(analysis_request)
            if self.sample_dict['_cls'].startswith('Sample.DomainSample'):
                self.do_analysis(analysis_request)
            else:
                msg = 'ERROR - No domain found to scan.'
                self.send_error_report(analysis_request, msg)

    def do_analysis(self, analysis_request):
        raise NotImplementedError('You need to inherit from this class and implement this method.')


class IPAnalysisClient(AnalysisClient):
    def __init__(self, config_object):
        super(IPAnalysisClient, self).__init__(config_object)

    def analyze(self, analysis_request):
        if 'sample' in analysis_request :
            self.sample_dict = get_sample_dict(analysis_request)
            if self.sample_dict['_cls'].startswith('Sample.IPSample'):
                self.do_analysis(analysis_request)
            else:
                msg = 'ERROR - No IP found to scan.'
                self.send_error_report(analysis_request, msg)

    def do_analysis(self, analysis_request):
        raise NotImplementedError('You need to inherit from this class and implement this method.')


