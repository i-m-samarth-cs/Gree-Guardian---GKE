import asyncio
import logging
import os
from flask import Flask, jsonify
from prometheus_client import start_http_server, Gauge, Counter
from energy_monitor import EnergyMonitor
from ai_optimizer import AIOptimizer
import threading

# Prometheus metrics
energy_consumption = Gauge('energy_consumption_kwh', 'Energy consumption in kWh', ['pod', 'namespace'])
carbon_emissions = Gauge('carbon_emissions_kg', 'Carbon emissions in kg CO2', ['pod', 'namespace'])
optimization_actions = Counter('optimization_actions_total', 'Total optimization actions taken')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GreenGuardianAgent:
    def __init__(self):
        self.energy_monitor = EnergyMonitor()
        self.ai_optimizer = AIOptimizer(os.getenv('GEMINI_API_KEY'))
        self.node_name = os.getenv('NODE_NAME')
        
    async def run(self):
        """Main agent loop"""
        logger.info(f"Starting Green Guardian Agent on node: {self.node_name}")
        
        while True:
            try:
                # Collect energy metrics
                metrics = await self.energy_monitor.collect_metrics()
                
                # Update Prometheus metrics
                for pod_metric in metrics:
                    energy_consumption.labels(
                        pod=pod_metric['pod_name'],
                        namespace=pod_metric['namespace']
                    ).set(pod_metric['energy_kwh'])
                    
                    carbon_emissions.labels(
                        pod=pod_metric['pod_name'],
                        namespace=pod_metric['namespace']
                    ).set(pod_metric['carbon_kg'])
                
                # AI optimization
                optimizations = await self.ai_optimizer.analyze_and_optimize(metrics)
                
                if optimizations:
                    optimization_actions.inc(len(optimizations))
                    logger.info(f"Applied {len(optimizations)} optimizations")
                
                # Wait before next collection
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                await asyncio.sleep(60)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/metrics/energy')
def get_energy_metrics():
    """Get current energy metrics"""
    try:
        # This would be called synchronously for API access
        metrics = asyncio.run(agent.energy_monitor.collect_metrics())
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start Prometheus metrics server
    start_http_server(8080)
    
    # Create agent instance
    agent = GreenGuardianAgent()
    
    # Start Flask app in background thread
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8081))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run main agent loop
    asyncio.run(agent.run())