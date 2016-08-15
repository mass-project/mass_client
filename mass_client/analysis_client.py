import re
from requests.exceptions import ConnectionError
from requests.exceptions import RequestException
import logging
import json
from tempfile import NamedTemporaryFile
from os import chmod
from .base_client import BaseClient
from contextlib import contextmanager
import datetime
from common_helper_encoder import ReportEncoder
import socket
import requests

# Log configuration
logger = logging.getLogger('mass_client_manager')
logger.setLevel(logging.INFO)


def _searialize_datetime(report_data):
    for key, value in report_data.items():
        if isinstance(value, datetime.datetime):
            report_data[key] = value.isoformat()


class AnalysisClient(BaseClient):
    """ Base class for analysis clients connecting to a MASS server.

    Do not use this class as a base class for analysis clients. Instead use one of the specific analysis client base classes
    or derive your own base class for a type of sample to analyse.
    """
    def __init__(self, config_object):
        super(AnalysisClient, self).__init__(config_object)
        self._instance_uuid = self._local_config['UUID']
        self._analysis_system_name = self._local_config['SystemName']
        self._analyses_in_progress = list()
        self._check_registration()

    def get_sample_dict(self, analysis_request):
        sample_url = analysis_request['sample']
        return self.http_client.get(sample_url).json()

    def download_sample_to_file(self, sample_url, file):
        r = self.http_client.get_stream(sample_url + 'download/')
        for block in r.iter_content(1024):
            if not block:
                break
            file.write(block)

    @contextmanager
    def temporary_sample_file(self):
        file = NamedTemporaryFile()
        chmod(file.name, 0o666)
        self.download_sample_to_file(self.sample_dict['url'], file)
        file.flush()
        yield file.name
        file.close()

    def _get_analysis_system_reference_url(self):
        return self._base_url + 'analysis_system/' + self._analysis_system_name + '/'

    def _register(self):
        registration_data = {
            'analysis_system': self._get_analysis_system_reference_url(),
            'uuid': self._instance_uuid
        }
        response = self.http_client.post_json(self._base_url + 'analysis_system_instance/', registration_data)

        if response.status_code != 201:
            logger.warn('Registration response: %s', response.text)
            return False
        else:
            return True

    def _is_registered(self):
        response = self.http_client.get(self._base_url + 'analysis_system_instance/' + self._instance_uuid + '/')
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

    def submit_ip(self, ip):
        """
        submit an IP sample to the MASS server
        """

        try:
            socket.inet_aton(ip)
        except:
            raise ValueError('{} is not a valid IP-address'.format(ip))
        json_data = {'ip_address': ip}
        response = self.http_client.post_json(self._base_url + 'sample/submit_ip/', data=json_data)
        if response.status_code != 201:
            raise RequestException('Could not post ip {}'.format(ip))
        logger.info('Submitted new IP {}'.format(ip))
        return json.loads(response.content.decode('utf-8'))

    def submit_dropped_by_sample_relation(self, archive_url, dropped_sample_url):
        """
        Submit a sample relation between a new file, which was dropped during the analysis, and the original file.

        :Example:
        virus.zip is analysed and contains virus.exe. The file gets
        extracted by the analysis client and then can submit the new file
        sample virus.exe and can submit that virus.exe was dropped by
        virus.zip.

            self.submit_dropped_by(self.sample_dict['url'], virus_url)

        """

        data = {
                "sample": dropped_sample_url,
                "other": archive_url,
                }

        response = self.http_client.post_json(self._base_url + 'sample_relation/submit_dropped_by/', data=data)
        if response.status_code != 201:
            raise RequestException('Could not post sample relation {} -- {}: {}'.format(dropped_sample_url, archive_url, response.content))
        return json.loads(response.content.decode('utf-8'))

    def submit_contacted_by_sample_relation(self, sample_url, contacted_ip):
        ip_sample_dict = self.submit_ip(contacted_ip)
        ip_sample_url = ''.join(ip_sample_dict['url'].split('?id=')) + '/'
        logger.info('New IP sample {}'.format(ip_sample_url))
        data = {
                "sample": ip_sample_url,
                "other": sample_url,
                }
        response = self.http_client.post_json(self._base_url + 'sample_relation/submit_contacted_by/', data=data)
        if response.status_code != 201:
            raise RequestException('Could not post sample relation {} -- {}: {}'.format(contacted_ip, sample_url, response.content))
        logger.info('Submitted new sample relation to {}'.format(contacted_ip))
        return json.loads(response.content.decode('utf-8'))

    def submit_report(self, analysis_url, analysis_date=datetime.datetime.utcnow(), status_code=0, error_message=None, tags=None,
                      additional_metadata=None, raw_report_objects=None, json_report_objects=None):
        """
        Submit the report from the analysis back to the MASS server.

        :Note:
            There are three ways to save the analysis result at MASS:

            * Additional Metadata: When the results of the analysis are very small and qualify as Meta Information, 
              e.g. the number of found IPs, if a static analysis was possitive etc., the results can be submitted as additional metadata.
              Note that it is crucial that the amount of meta data stays small. 
              Otherwise it will become increasingly slower to load the report API endpoint since all metadata are contained in the report JSON object.
            * JSON Report: If the analysis report can be encoded by the python JSON module it is advisable to submit the report as a JSON object.
              This will make it later easier to extract information from the report in an automated way. 
              See the parameter description for how to submit a JSON Report.
            * Raw Report: If the report of the analysis can not be encoded as an JSON object easily, e.g. pictures, pcap files, then submit a raw report.
              See the parameter description for how to submit a JSON Report.

        :param analysis_url: URL of the analysis request.
        :param analysis_date: Datetime of the analysis. Default is datetime.datetime.utcnow()
        :param additional_metadata: Dictionary of the analysis results. 
        :param raw_report_objects: Dictionary of the raw analysis results. The dictionary should be of the form {'report_description1' : json_report_object1, ... }.
        :param json_report_objects: Dictionary of the analysis results. The dictionary should be of the form {'report_description1' : raw_report_object1, ... }.
        :param tags: Tags to be added to the report for easier searching.
        :param error_message: Message added to the report if an error occured during the analysis which cannot be resolved. See also the send_error_report function.
        :param status_code: Status code for the ananlysis. The value should be 0 if the analysis could be performed without errors. See also the send_error_report function.
        """

        if raw_report_objects is None:
            raw_report_objects = dict()
        if additional_metadata is None:
            additional_metadata = dict()
        if tags is None:
            tags = []
        if json_report_objects is None:
            json_report_objects = dict()

        report_metadata = {
            'analysis_date': analysis_date,
            'status': status_code,
            'error_message': error_message,
            'tags': tags,
            'additional_metadata': additional_metadata
        }
        _searialize_datetime(report_metadata)

        files = {'metadata': ('metadata', json.dumps(report_metadata, cls=ReportEncoder), 'application/json')}

        for name, value in raw_report_objects.items():
            files[name] = (name, open(value, 'rb'), 'binary/octet-stream')

        for name, value in json_report_objects.items():
            files[name] = (name, json.dumps(value, cls=ReportEncoder), 'application/json')

        self._analyses_in_progress.remove(analysis_url)
        response = self.http_client.post_files(analysis_url + 'submit_report/', files=files)

        if response.status_code != 204:
            logger.warn('Creating report failed: %s', response.text)
            return False
        else:
            return True

    def _handover_scheduled_analysis_to_application(self, analysis_url):
        self._analyses_in_progress.append(analysis_url)
        response = self.http_client.get(analysis_url)

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
        """ Poll the MASS server for new scheduled analysis requests. If there are new requests they will be analysed sequentially.
        """
        try:
            logger.info('Polling for scheduled analysis.')

            # Get analysis list
            response = self.http_client.get(self._base_url + 'analysis_system_instance/' + self._instance_uuid + '/scheduled_analyses/')
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
        """
        If an error occured during the analysis which can not be resolved by the
        analysis client, use this function to send an error report to the MASS
        server.

        :param data: The analysis request which caused the error.
        :param msg: Additional information about the error.
        :type data: dictionary
        :type msg: string
        """
        self.submit_report(data['url'], status_code=1, error_message=msg)
        return


class FileAnalysisClient(AnalysisClient):
    """ Base class for analysis clients to analyse files.

    Derive your specific analysis client class from this base class.
    """
    def __init__(self, config_object):
        super(FileAnalysisClient, self).__init__(config_object)

    def analyze(self, analysis_request):
        """ Ensure that the analysis request was made for a file sample or a sub-type and perform the analysis.
        """
        if 'sample' in analysis_request:
            self.sample_dict = self.get_sample_dict(analysis_request)
            if self.sample_dict['_cls'].startswith('Sample.FileSample'):
                self.do_analysis(analysis_request)
            else:
                msg = 'ERROR - No file found to scan.'
                self.send_error_report(analysis_request, msg)

    def do_analysis(self, analysis_request):
        """ Do the actual analysis. Overwrite this function in your derived class.
        """
        raise NotImplementedError('You need to inherit from this class and implement this method.')


class DomainAnalysisClient(AnalysisClient):
    """ Base class for analysis clients to analyse domains.

    Derive your specific analysis client class from this base class.
    """

    def __init__(self, config_object):
        super(DomainAnalysisClient, self).__init__(config_object)

    def analyze(self, analysis_request):
        """ Ensure that the analysis request was made for a domain sample or a sub-type and perform the analysis.
        """

        if 'sample' in analysis_request:
            self.sample_dict = self.get_sample_dict(analysis_request)
            if self.sample_dict['_cls'].startswith('Sample.DomainSample'):
                self.do_analysis(analysis_request)
            else:
                msg = 'ERROR - No domain found to scan.'
                self.send_error_report(analysis_request, msg)

    def do_analysis(self, analysis_request):
        raise NotImplementedError('You need to inherit from this class and implement this method.')


class IPAnalysisClient(AnalysisClient):
    """ Base class for analysis clients to analyse IP addresses.

    Derive your specific analysis client class from this base class.
    """

    def __init__(self, config_object):
        super(IPAnalysisClient, self).__init__(config_object)

    def analyze(self, analysis_request):
        """ Ensure that the analysis request was made for an IP sample or a sub-type and perform the analysis.
        """

        if 'sample' in analysis_request:
            self.sample_dict = self.get_sample_dict(analysis_request)
            if self.sample_dict['_cls'].startswith('Sample.IPSample'):
                self.do_analysis(analysis_request)
            else:
                msg = 'ERROR - No IP found to scan.'
                self.send_error_report(analysis_request, msg)

    def do_analysis(self, analysis_request):
        raise NotImplementedError('You need to inherit from this class and implement this method.')


class URIAnalysisClient(AnalysisClient):
    """ Base class for analysis clients to analyse URIs.

    Derive your specific analysis client class from this base class.
    """

    def __init__(self, config_object):
        super(URIAnalysisClient, self).__init__(config_object)

    def analyze(self, analysis_request):
        """ Ensure that the analysis request was made for an URI sample or a sub-type and perform the analysis.
        """

        if 'sample' in analysis_request:
            self.sample_dict = self.get_sample_dict(analysis_request)
            if self.sample_dict['_cls'].startswith('Sample.URISample'):
                self.do_analysis(analysis_request)
            else:
                msg = 'ERROR - No URI found to scan.'
                self.send_error_report(analysis_request, msg)

    def do_analysis(self, analysis_request):
        raise NotImplementedError('You need to inherit from this class and implement this method.')

