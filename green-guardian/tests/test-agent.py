import unittest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the agent directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from energy_monitor import EnergyMonitor
from ai_optimizer import AIOptimizer

class TestEnergyMonitor(unittest.TestCase):
    def setUp(self):
        self.energy_monitor = EnergyMonitor()
    
    @patch('energy_monitor.client')
    def test_collect_metrics(self, mock_client):
        # Mock Kubernetes client responses
        mock_metrics_response = {
            'items': [
                {
                    'metadata': {
                        'name': 'test-pod',
                        'namespace': 'default'
                    },
                    'containers': [
                        {
                            'usage': {
                                'cpu': '100000000n',  # 0.1 CPU cores
                                'memory': '128Mi'
                            }
                        }
                    ],
                    'timestamp': '2023-01-01T00:00:00Z'
                }
            ]
        }
        
        mock_client.CustomObjectsApi().list_namespaced_custom_object.return_value = mock_metrics_response
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            metrics = loop.run_until_complete(self.energy_monitor.collect_metrics())
            
            self.assertGreater(len(metrics), 0)
            self.assertIn('pod_name', metrics[0])
            self.assertIn('energy_kwh', metrics[0])
            self.assertIn('carbon_kg', metrics[0])
        finally:
            loop.close()
    
    def test_parse_memory(self):
        # Test memory parsing
        self.assertEqual(self.energy_monitor._parse_memory('128Ki'), 128 * 1024)
        self.assertEqual(self.energy_monitor._parse_memory('256Mi'), 256 * 1024 * 1024)
        self.assertEqual(self.energy_monitor._parse_memory('1Gi'), 1 * 1024 * 1024 * 1024)

class TestAIOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = AIOptimizer('test-api-key')
    
    @patch('ai_optimizer.aiohttp.ClientSession.post')
    def test_analyze_with_gemini(self, mock_post):
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'candidates': [{
                'content': {
                    'parts': [{
                        'text': json.dumps({
                            'anomalies': ['test-pod'],
                            'optimization_opportunities': [{
                                'pod': 'test-pod',
                                'namespace': 'default',
                                'type': 'scale_down',
                                'confidence': 0.8,
                                'reason': 'Low utilization',
                                'estimated_savings_kwh': 0.01,
                                'parameters': {}
                            }],
                            'cluster_insights': 'Test insights'
                        })
                    }]
                }
            }]
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Test data
        test_metrics = [{
            'pod_name': 'test-pod',
            'namespace': 'default',
            'energy_kwh': 0.05,
            'carbon_kg': 0.02,
            'cpu_usage': 0.1,
            'memory_usage': 0.5
        }]
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self.optimizer._analyze_with_gemini(test_metrics))
            
            self.assertIn('optimization_opportunities', result)
            self.assertEqual(len(result['optimization_opportunities']), 1)
            self.assertEqual(result['optimization_opportunities'][0]['pod'], 'test-pod')
        finally:
            loop.close()

if __name__ == '__main__':
    unittest.main()
