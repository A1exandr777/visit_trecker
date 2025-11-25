import unittest
from unittest.mock import patch, MagicMock
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from pathlib import Path
import json
import os
from datetime import datetime

import main

TEST_DATA_FILE = Path("test_visits.json")

class TestLogicFunctions(unittest.TestCase):

    def setUp(self):
        self.original_data_file = main.DATA_FILE
        main.DATA_FILE = TEST_DATA_FILE

    def tearDown(self):
        if TEST_DATA_FILE.exists():
            os.remove(TEST_DATA_FILE)
        main.DATA_FILE = self.original_data_file

    def test_load_data_partial_data(self):
        with TEST_DATA_FILE.open('w') as f:
            json.dump({'total': 500}, f)
        data = main.load_data()
        self.assertEqual(data['total'], 500)
        self.assertIn('unique_total', data)
        self.assertEqual(data['unique_total'], 0)

    def test_save_and_load_cycle(self):
        data_to_save = {'total': 123, 'unique_ips': ['1.2.3.4']}
        main.save_data(data_to_save)
        loaded_data = main.load_data()
        self.assertEqual(loaded_data['total'], 123)
        self.assertEqual(loaded_data['unique_ips'], ['1.2.3.4'])

    def test_increment_counters(self):
        data = main.load_data()

        main.increment_counters(data, '1.1.1.1')
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['unique_total'], 1)
        self.assertEqual(data['unique_by_day'][datetime.now().strftime('%Y-%m-%d')]['count'], 1)

        main.increment_counters(data, '1.1.1.1')
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['unique_total'], 1)
        self.assertEqual(data['unique_by_day'][datetime.now().strftime('%Y-%m-%d')]['count'], 1)

        main.increment_counters(data, '2.2.2.2')
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['unique_total'], 2)
        self.assertEqual(data['unique_by_day'][datetime.now().strftime('%Y-%m-%d')]['count'], 2)

    @patch('main.datetime')
    def test_increment_counters_date_change(self, mock_datetime):
        data = main.load_data()

        mock_datetime.now.return_value = datetime(2025, 10, 14)
        main.increment_counters(data, '1.1.1.1')
        self.assertIn('2025-10-14', data['by_day'])
        self.assertEqual(data['by_day']['2025-10-14'], 1)

        mock_datetime.now.return_value = datetime(2025, 10, 15)
        main.increment_counters(data, '1.1.1.1')
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['unique_total'], 1)
        self.assertIn('2025-10-15', data['by_day'])
        self.assertEqual(data['by_day']['2025-10-15'], 1)
        self.assertEqual(data['unique_by_day']['2025-10-15']['count'], 1)

        mock_datetime.now.return_value = datetime(2025, 11, 1)
        main.increment_counters(data, '3.3.3.3')
        self.assertIn('2025-11', data['by_month'])
        self.assertEqual(data['by_month']['2025-11'], 1)
        self.assertEqual(data['unique_by_month']['2025-11']['count'], 1)

    def test_reset_counters(self):
        data = {'total': 100, 'unique_ips': ['1.1.1.1']}
        main.reset_counters(data)
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['unique_total'], 0)
        self.assertEqual(data['unique_ips'], [])
        self.assertEqual(data['by_day'], {})

    def test_get_client_ip(self):
        mock_request = MagicMock()
        mock_request.headers = {'X-Forwarded-For': '1.1.1.1'}
        self.assertEqual(main.get_client_ip(mock_request), '1.1.1.1')

        mock_request.headers = {'X-Forwarded-For': '1.1.1.1, 2.2.2.2, 3.3.3.3'}
        self.assertEqual(main.get_client_ip(mock_request), '1.1.1.1')

        mock_request.headers = {}
        mock_request.remote = '4.4.4.4'
        self.assertEqual(main.get_client_ip(mock_request), '4.4.4.4')

        mock_request.remote = None
        self.assertEqual(main.get_client_ip(mock_request), 'unknown')


class CounterAppTestCase(AioHTTPTestCase):

    async def get_application(self):
        return main.create_app()

    def setUp(self):
        self.original_data_file = main.DATA_FILE
        main.DATA_FILE = TEST_DATA_FILE
        super().setUp()

    def tearDown(self):
        if TEST_DATA_FILE.exists():
            os.remove(TEST_DATA_FILE)
        main.DATA_FILE = self.original_data_file
        super().tearDown()

    @unittest_run_loop
    async def test_full_workflow(self):
        resp = await self.client.request("GET", "/count")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['unique_total'], 0)

        resp = await self.client.request("GET", "/", headers={'X-Forwarded-For': '1.1.1.1'})
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.content_type, 'text/html')
        text = await resp.text()
        self.assertIn("Всего посещений: <strong>1</strong>", text)
        self.assertIn("Всего уникальных: <strong>1</strong>", text)

        await self.client.request("GET", "/", headers={'X-Forwarded-For': '1.1.1.1'})
        resp = await self.client.request("GET", "/count")
        data = await resp.json()
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['unique_total'], 1)

        await self.client.request("GET", "/", headers={'X-Forwarded-For': '2.2.2.2'})
        resp = await self.client.request("GET", "/count")
        data = await resp.json()
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['unique_total'], 2)
        self.assertEqual(data['unique_today'], 2)

        resp = await self.client.request("POST", "/reset")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.content_type, 'application/json')
        reset_data = await resp.json()
        self.assertEqual(reset_data['status'], 'ok')

        resp = await self.client.request("GET", "/")
        text = await resp.text()
        self.assertIn("Всего посещений: <strong>1</strong>", text)
        self.assertIn("Всего уникальных: <strong>1</strong>", text)
        resp = await self.client.request("GET", "/count")
        data = await resp.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['unique_total'], 1)

    @unittest_run_loop
    async def test_reset_api_method_not_allowed(self):
        resp = await self.client.request("GET", "/reset")
        self.assertEqual(resp.status, 405)


if __name__ == '__main__':
    unittest.main(verbosity=2)