import unittest
from httmock import urlmatch, HTTMock
from mass_client import get_sample_dict
import json

class GetSampleDictTestCase(unittest.TestCase):
    def test_get_sample_dict(self):
        analysis_request = {
                'sample' : 'http://mass_server.de/sample/1'
                }

        mock_sample = {
                'id' : 'some_id'
                }

        @urlmatch(netloc=r'mass_server.de', path=r'/sample/\d*')
        def mass_mock(url, request):
            return json.dumps(mock_sample).encode('utf-8')

        with HTTMock(mass_mock):
            sample_dict = get_sample_dict(analysis_request)

        self.assertIn('id', sample_dict)
        self.assertEqual(sample_dict['id'], mock_sample['id'])


class 
