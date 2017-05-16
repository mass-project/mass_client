import logging
import mass_api_client.resources as mass_resources
from mass_api_client import ConnectionManager
from mass_api_client.resources import Report
import time
from requests.exceptions import HTTPError

# Log configuration
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def _add_filename(report_dict):
    if report_dict:
        for report_key, report in report_dict.items():
            report_dict[report_key] = (report_key, report)
    return report_dict


def _create_or_get_analysis_system(identifier, verbose_name='', tag_filter=''):
    try:
        analysis_system = mass_resources.AnalysisSystem.get(identifier)
    except HTTPError:
        analysis_system = mass_resources.AnalysisSystem.create(identifier, verbose_name, tag_filter)
    return analysis_system

def get_instance_from_config(config):
    if 'uuid' in config['Client']:
        return mass_resources.AnalysisSystemInstance.get(config['Client']['uuid'])
    else:
        client_config = config['Client']
        ana_sys = _create_or_get_analysis_system(client_config['identifier'], client_config['verbosename'], client_config['filterexpression'])
        return ana_sys.create_analysis_system_instance()

def analysis_queue(analysis_system_instance, poll_time=60, sleep_time=10):
    """ Generator yielding scheduled analyses from the queue of a Analysis System Instance.
    """
    log.info('Starting the poll loop.')
    time_since_last_poll = 0
    do_poll = True
    while True:
        if do_poll is True:
            log.info('Polling for scheduled analyses.')
            analysis_list = analysis_system_instance.get_scheduled_analyses()
            for scheduled_analysis in analysis_list:
                log.info('Analyzsing {}'.format(scheduled_analysis))
                yield scheduled_analysis
            do_poll = False
        else:
            time.sleep(sleep_time)
            time_since_last_poll += sleep_time
            if time_since_last_poll >= poll_time:
                time_since_last_poll = 0
                do_poll = True
            else:
                do_poll = False

def submit_report(scheduled_analysis, additional_metadata={}, json_report_objects=None, raw_report_objects=None):
    Report.create(
        scheduled_analysis,
        json_report_objects=_add_filename(json_report_objects),
        raw_report_objects=_add_filename(raw_report_objects),
        additional_metadata=additional_metadata
    )


class AnalysisClient():
    """ Base class for analysis clients connecting to a MASS server.

    Do not use this class as a base class for analysis clients. Instead use one of the specific analysis client base classes
    or derive your own base class for a type of sample to analyse.
    """
    def __init__(self, config):
        base_config = config['Base']
        client_config = config['Client']
        ConnectionManager().register_connection('default', base_config['ApiKey'], base_config['Server'])
        if 'UUID' in client_config.keys():
            self._analysis_system_instance = mass_resources.AnalysisSystemInstance.get(client_config['UUID'])
        else:
            identifier = client_config['Identifier']
            try:
                self._analysis_system = mass_resources.AnalysisSystem.get(identifier)
            except HTTPError: 
                verbose_name = client_config['VerboseName']
                tag_filter_expression = client_config.get('FilterExpression', '')
                self._analysis_system = mass_resources.AnalysisSystem.create(identifier, verbose_name, tag_filter_expression)
            self._analysis_system_instance = self._analysis_system.create_analysis_system_instance()
        log.info('Got analysis system instance {}'.format(self._analysis_system_instance))
        self._sleep_time = base_config.getint('SleepTime')
        self._poll_time = base_config.getint('PollTime')

    def analyze(self, scheduled_analysis):
        """Process the analysis request.

        Do whatever it take to analyse the sample in the request.
        Afterwards send a report with the results or an error to the MASS server to close the request.
        """
        raise NotImplementedError('This method needs to be implemented by a class derived from AnalysisClient')

    def start(self):
        log.info('Starting the analysis client.')
        for scheduled_analysis in analysis_queue(self._analysis_system_instance, poll_time=self._poll_time, sleep_time=self._sleep_time):
            self.analyze(scheduled_analysis)

    def submit_report(self, scheduled_analysis, additional_metadata={}, json_report_objects=None, raw_report_objects=None):
        submit_report(scheduled_analysis, additional_metadata, json_report_objects, raw_report_objects)
