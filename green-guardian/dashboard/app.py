from flask import Flask, render_template, jsonify, request
import requests
import json
from datetime import datetime, timedelta
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')

class DashboardAPI:
    def __init__(self):
        self.prometheus_url = PROMETHEUS_URL
    
    def query_prometheus(self, query: str, time_range: str = '1h'):
        """Query Prometheus for metrics"""
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {'query': query}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Prometheus query failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None
    
    def query_range(self, query: str, start: datetime, end: datetime, step: str = '1m'):
        """Query Prometheus for time series data"""
        try:
            url = f"{self.prometheus_url}/api/v1/query_range"
            params = {
                'query': query,
                'start': start.timestamp(),
                'end': end.timestamp(),
                'step': step
            }
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Prometheus range query failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error querying Prometheus range: {e}")
            return None

dashboard_api = DashboardAPI()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/current-metrics')
def current_metrics():
    """Get current energy metrics"""
    try:
        # Query current energy consumption
        energy_query = 'energy_consumption_kwh'
        energy_data = dashboard_api.query_prometheus(energy_query)
        
        # Query current carbon emissions
        carbon_query = 'carbon_emissions_kg'
        carbon_data = dashboard_api.query_prometheus(carbon_query)
        
        # Query optimization actions
        actions_query = 'optimization_actions_total'
        actions_data = dashboard_api.query_prometheus(actions_query)
        
        # Process and format data
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'total_energy_kwh': 0,
            'total_carbon_kg': 0,
            'total_optimizations': 0,
            'pods': []
        }
        
        if energy_data and energy_data['status'] == 'success':
            for result in energy_data['data']['result']:
                pod_name = result['metric'].get('pod', 'unknown')
                namespace = result['metric'].get('namespace', 'default')
                energy_value = float(result['value'][1])
                
                metrics['total_energy_kwh'] += energy_value
                
                # Find corresponding carbon data
                carbon_value = 0
                if carbon_data and carbon_data['status'] == 'success':
                    for carbon_result in carbon_data['data']['result']:
                        if (carbon_result['metric'].get('pod') == pod_name and 
                            carbon_result['metric'].get('namespace') == namespace):
                            carbon_value = float(carbon_result['value'][1])
                            break
                
                metrics['total_carbon_kg'] += carbon_value
                
                metrics['pods'].append({
                    'name': pod_name,
                    'namespace': namespace,
                    'energy_kwh': energy_value,
                    'carbon_kg': carbon_value
                })
        
        if actions_data and actions_data['status'] == 'success':
            for result in actions_data['data']['result']:
                metrics['total_optimizations'] += float(result['value'][1])
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical-data')
def historical_data():
    """Get historical energy data for charts"""
    try:
        hours = int(request.args.get('hours', 24))
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Query historical energy consumption
        energy_query = 'sum(energy_consumption_kwh)'
        energy_data = dashboard_api.query_range(energy_query, start_time, end_time, '5m')
        
        # Query historical carbon emissions
        carbon_query = 'sum(carbon_emissions_kg)'
        carbon_data = dashboard_api.query_range(carbon_query, start_time, end_time, '5m')
        
        historical = {
            'timeRange': f'{hours}h',
            'energy_series': [],
            'carbon_series': []
        }
        
        if energy_data and energy_data['status'] == 'success':
            for result in energy_data['data']['result']:
                for timestamp, value in result['values']:
                    historical['energy_series'].append({
                        'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                        'value': float(value)
                    })
        
        if carbon_data and carbon_data['status'] == 'success':
            for result in carbon_data['data']['result']:
                for timestamp, value in result['values']:
                    historical['carbon_series'].append({
                        'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                        'value': float(value)
                    })
        
        return jsonify(historical)
        
    except Exception as e:
        logger.error(f"Error getting historical data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pod-details/<namespace>/<pod_name>')
def pod_details(namespace, pod_name):
    """Get detailed metrics for a specific pod"""
    try:
        # Query pod-specific metrics
        energy_query = f'energy_consumption_kwh{{pod="{pod_name}",namespace="{namespace}"}}'
        carbon_query = f'carbon_emissions_kg{{pod="{pod_name}",namespace="{namespace}"}}'
        
        energy_data = dashboard_api.query_prometheus(energy_query)
        carbon_data = dashboard_api.query_prometheus(carbon_query)
        
        details = {
            'pod_name': pod_name,
            'namespace': namespace,
            'current_energy_kwh': 0,
            'current_carbon_kg': 0,
            'efficiency_score': 85,  # Mock score for demo
            'recommendations': [
                "Consider reducing CPU requests by 20%",
                "Memory usage is optimal",
                "Pod could benefit from horizontal scaling"
            ]
        }
        
        if energy_data and energy_data['status'] == 'success' and energy_data['data']['result']:
            details['current_energy_kwh'] = float(energy_data['data']['result'][0]['value'][1])
        
        if carbon_data and carbon_data['status'] == 'success' and carbon_data['data']['result']:
            details['current_carbon_kg'] = float(carbon_data['data']['result'][0]['value'][1])
        
        return jsonify(details)
        
    except Exception as e:
        logger.error(f"Error getting pod details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/savings-report')
def savings_report():
    """Generate savings report from optimizations"""
    try:
        # Mock savings data - in production this would come from historical optimization results
        report = {
            'period': '30 days',
            'total_energy_saved_kwh': 45.7,
            'total_carbon_saved_kg': 21.6,
            'cost_savings_usd': 12.45,
            'optimizations_applied': 127,
            'top_optimizations': [
                {
                    'type': 'Resource Right-sizing',
                    'energy_saved_kwh': 18.3,
                    'occurrences': 45
                },
                {
                    'type': 'Pod Scaling',
                    'energy_saved_kwh': 15.2,
                    'occurrences': 32
                },
                {
                    'type': 'Idle Detection',
                    'energy_saved_kwh': 12.2,
                    'occurrences': 50
                }
            ],
            'efficiency_trend': 'improving',
            'projected_monthly_savings': {
                'energy_kwh': 61.2,
                'carbon_kg': 29.0,
                'cost_usd': 16.70
            }
        }
        
        return jsonify(report)
        
    except Exception as e:
        logger.error(f"Error generating savings report: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)