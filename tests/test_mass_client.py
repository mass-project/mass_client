import unittest
import mass_client
import itertools
from unittest import mock


class AnalysisSystemInstanceMock:
    def __init__(self, scheduled_analyses):
        self.scheduled_analyses = scheduled_analyses
        self.next_idx = 0

    def get_scheduled_analyses(self):
        try:
            analyses = self.scheduled_analyses[self.next_idx]
        except IndexError:
            return []
        self.next_idx += 1
        return analyses


class MassClientTestCase(unittest.TestCase):

    @mock.patch('time.sleep', return_value=None)
    def test_analysis_queue(self, sleep_mock):
        analyses = [['foo', 'bar', 'blup'],
                    ['fii', 'faa', 'foo'],
                    ['baz']]
        instance = AnalysisSystemInstanceMock(analyses)
        all_analyses = list(itertools.chain(*analyses))
        poll_time = 60
        sleep_time = 10
        for scheduled_analysis, idx in zip(mass_client.analysis_queue(instance, 60, 10), range(len(all_analyses)-1)):
            self.assertIn(scheduled_analysis, all_analyses)
        self.assertEqual(sleep_mock.call_count, 2*(poll_time/sleep_time))
        
