import unittest
import json
from unittest.mock import patch, Mock
import sys
import os

# Add the dashboard directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'dashboard'))

from app import app, DashboardAPI

class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.dashboard_api = DashboardAPI()
    
    def test_index_route(self):
        """Test the main dashboard page loads"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Green Guardian', response.data)
    
    @patch('app.dashboard_api.query_prometheus')
    def test_current_metrics_api(self, mock_query):
        """Test the current metrics API endpoint"""
        # Mock Prometheus responses
        mock_query.side_effect = [
            # Energy query response
            {
                'status': 'success',
                'data': {
                    'result': [
                        {
                            'metric': {'pod': 'test-pod', 'namespace': 'default'},
                            'value': [1234567890, '0.05']
                        }
                    ]
                }
            },
            # Carbon query response
            {
                'status': 'success',
                'data': {
                    'result': [
                        {
                            'metric': {'pod': 'test-pod', 'namespace': 'default'},
                            'value': [1234567890, '0.02']
                        }
                    ]
                }
            },
            # Actions query response
            {
                'status': 'success',
                'data': {
                    'result': [
                        {
                            'metric': {},
                            'value': [1234567890, '5']
                        }
                    ]
                }
            }
        ]
        
        response = self.app.get('/api/current-metrics')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('total_energy_kwh', data)
        self.assertIn('total_carbon_kg', data)
        self.assertIn('pods', data)
        self.assertEqual(data['total_energy_kwh'], 0.05)
        self.assertEqual(data['total_carbon_kg'], 0.02)
    
    @patch('requests.get')
    def test_prometheus_query(self, mock_get):
        """Test Prometheus query functionality"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'data': {'result': []}
        }
        mock_get.return_value = mock_response
        
        result = self.dashboard_api.query_prometheus('test_metric')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'success')
        mock_get.assert_called_once()
    
    def test_savings_report_api(self):
        """Test the savings report API endpoint"""
        response = self.app.get('/api/savings-report')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('total_energy_saved_kwh', data)
        self.assertIn('total_carbon_saved_kg', data)
        self.assertIn('cost_savings_usd', data)

if __name__ == '__main__':
    unittest.main()
