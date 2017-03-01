import logging
import mass_api_client.resources as mass_resources
from mass_api_client import ConnectionManager
from mass_api_client.resources import Report
import time
import configparser

# Log configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
shandler = logging.StreamHandler()
shandler.setLevel(logging.INFO)
logger.addHandler(shandler)


def _add_filename(report_dict):
    if report_dict:
        for report_key, report in report_dict.items():
            report_dict[report_key] = (report_key, report)
    return report_dict


class AnalysisClient(mass_resources.AnalysisSystem):
    """ Base class for analysis clients connecting to a MASS server.

    Do not use this class as a base class for analysis clients. Instead use one of the specific analysis client base classes
    or derive your own base class for a type of sample to analyse.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._analyses_in_progress = list()
        self._should_terminate = False

    def submit_report(self, scheduled_analysis, additional_metadata=None, json_report_objects=None, raw_report_objects=None):
        Report.create(
            scheduled_analysis,
            json_report_objects=_add_filename(json_report_objects),
            raw_report_objects=_add_filename(raw_report_objects),
            additional_metadata=additional_metadata
        )


    @classmethod
    def create_from_config(cls, config_path):
        config = configparser.ConfigParser()
        config.read_file(open(config_path, 'r'))
        base_config = config['Base']
        client_config = config['Client']
        ConnectionManager().register_connection('default', base_config['ApiKey'], base_config['Server'])
        if 'UUID' in client_config.keys():
            self = cls.get(client_config['Identifier'])
            self._analysis_system_instance = mass_resources.AnalysisSystemInstance.get(client_config['UUID'])
        else:
            identifier = client_config['Identifier']
            verbose_name = client_config['VerboseName']
            tag_filter_expression = client_config.get('FilterExpression', '')
            self = cls.create(identifier, verbose_name, tag_filter_expression)
            self._analysis_system_instance = self.create_analysis_system_instance()
            config['Client']['UUID'] = self._analysis_system_instance.uuid
            config.write(open(config_path, 'w'))
        self._sleep_time = base_config.getint('SleepTime')
        self._poll_time = base_config.getint('PollTime')
        return self

    def analyze(self, scheduled_analysis):
        """Process the analysis request.

        Do whatever it take to analyse the sample in the request.
        Afterwards send a report with the results or an error to the MASS server to close the request.
        """
        raise NotImplementedError('This method needs to be implemented by a class derived from AnalysisClient')

    def stop(self):
        self._should_terminate = True

    def start(self):
        logger.info('Starting the analysis client.')
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

    def poll_server(self):
        """ Poll the MASS server for new scheduled analysis requests. If there are new requests they will be analysed sequentially.
        """
        logger.info('Polling for scheduled analyses.')

        # See if there is something to do
        analysis_list = self._analysis_system_instance.get_scheduled_analyses()
        processed_analyses = 0
        for scheduled_analysis in analysis_list:
            if self._should_terminate is True:
                return True
            # If this analysis is already in progress, skip it
            if scheduled_analysis in self._analyses_in_progress:
                continue
            # Do the analysis
            self.analyze(scheduled_analysis)
            processed_analyses += 1
