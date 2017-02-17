"""
AnalysisClient
==============

Example
--------------


"""

import re
import logging
import json
from tempfile import NamedTemporaryFile
from os import chmod
from .base_client import BaseClient
from contextlib import contextmanager
import datetime
import mass_api_client.resources as mass_resources
from mass_api_client import ConnectionManager
from requests.exceptions import HTTPError
import threading
import time

# Log configuration
logger = logging.getLogger('mass_client_manager')
logger.setLevel(logging.INFO)



class AnalysisClient(mass_resources.AnalysisSystem):
    """ Base class for analysis clients connecting to a MASS server.

    Do not use this class as a base class for analysis clients. Instead use one of the specific analysis client base classes
    or derive your own base class for a type of sample to analyse.
    """
    @classmethod
    def get_or_create(cls, config):
        """Create an AnalysisClient from the given config unless the analysis system already exists on the server.
        """
        local_config = config[cls.__name__]
        mass_url = local_config['ServerURL']
        api_key = local_config['ApiKey']
        identifier_name = local_config['IdentifierName']
        verbose_name = local_config['VerboseName']
        tag_filter_expression = local_config['TagFilerExpression']
        ConnectionManager().register_connection('default', api_key, mass_url)
        try:
            analysis_client = cls.get(identifier_name)
        except HTTPError():
            analysis_client = cls.create(identifier_name=identifier_name, verbose_name=verbose_name, tag_filter_expression=tag_filter_expression)
        analysis_client.config = local_config
        return analysis_client

    def create_analysis_system_instance(self):
        """Create the analysis client from the given config

        If the analysis client already exists at the server
        """
        # TODO call either AnalysisSystemInstance.create(analysis_system=self) or AnalysisClient.get(uuid)
        if 'UUID' in self.local_config.keys():
            return mass_resources.AnalysisSystemInstance.get(self.local_config['UUID'])
        else:
            # TODO don't forget to write UUID to config
            self.create_analysis_system_instance()
            

    def analyze(self, analysis_request):
        raise NotImplementedError('This method needs to be implemented by a class derived from AnalysisClient')

    def send_error_report(self, data, msg):
        raise NotImplementedError('Use mass_api_client resource Report instead.')

    def submit_ip(self, ip):
        raise NotImplementedError('Use mass_api_client resource IP instead.')

    def submit_dropped_by_sample_relation(self, archive_url, dropped_sample_url):
        raise NotImplementedError('Use mass_api_client resource DroppedBySampleRelation instead')

    def submit_contacted_by_sample_relation(self, sample_url, contacted_ip):
        raise NotImplementedError('Use mass_api_client resources IPSample and ContactedBySampleRelation instead.')

    def submit_report(self, analysis_url, analysis_date=datetime.datetime.utcnow(), status_code=0, error_message=None, tags=None, additional_metadata=None, raw_report_objects=None, json_report_objects=None):
        raise NotImplementedError('Use mass_api_client resource Report.')

    def get_sample(self, analysis_request):
        return NotImplementedError('Use mass_api_client resource AnalysisRequest._get_sample method.')


class AnalysisClientsDriver(threading.Thread):
    def __init__(self, analysis_system, config):
        if 'Driver' not in config.keys():
            raise
        self._config = config['Driver']
        self._sleep_time = int(self._config['SleepTime'])
        self._poll_time = int(self._config['PollTime'])
        self._analysis_system = analysis_system.create_from_config(config)
        self._analysis_system_instance = self._analysis_system.create_analysis_system_instance()
        self._analyses_in_progress = list()

    def _handover_scheduled_analysis_to_analysis_system(self, analysis_request):
        self._analyses_in_progress.append(analysis_request)

        # TODO Check if the UUID is equal to our UUID
        logger.info('Analyzing analysis request {} on system {} with instance {}'.format(analysis_request, self._analysis_system))
        self._analysis_system.analyze(analysis_request)

    def poll_server(self):
        """ Poll the MASS server for new scheduled analysis requests. If there are new requests they will be analysed sequentially.
        """
        logger.info('Polling for scheduled analysis.')

        # See if there is something to do
        analysis_list = self._analysis_system_instance.get_scheduled_analyses()
        processed_analyses = 0
        for analysis in analysis_list:
            if self._should_terminate is True:
                return True
            # If this analysis is already in progress, skip it
            if analysis in self._analyses_in_progress:
                continue
            # Do the analysis
            self._handover_scheduled_analysis_to_analysis_system(analysis)
            processed_analyses += 1
        logger.error('MASS server not reachable. Trying again ...')

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


