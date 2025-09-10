import psutil
import asyncio
import aiohttp
import json
from kubernetes import client, config
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class EnergyMonitor:
    def __init__(self):
        # Load Kubernetes config
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.metrics_v1 = client.CustomObjectsApi()
        
        # CPU TDP values (Watts) - simplified mapping
        self.cpu_tdp_map = {
            'intel': {'default': 95, 'low_power': 35, 'high_perf': 165},
            'amd': {'default': 105, 'low_power': 45, 'high_perf': 180}
        }
        
    async def get_carbon_intensity(self) -> float:
        """Get current carbon intensity from external API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Using a mock API - replace with actual carbon intensity service
                async with session.get('https://api.carbonintensity.org.uk/intensity') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['data'][0]['intensity']['actual'] / 1000  # Convert to kg CO2/kWh
        except Exception as e:
            logger.warning(f"Could not fetch carbon intensity: {e}")
        
        # Default carbon intensity (global average)
        return 0.475  # kg CO2/kWh
    
    async def collect_metrics(self) -> List[Dict]:
        """Collect energy metrics for all pods on this node"""
        metrics = []
        carbon_intensity = await self.get_carbon_intensity()
        
        try:
            # Get pod metrics from Kubernetes metrics API
            pod_metrics = self.metrics_v1.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace="",
                plural="pods"
            )
            
            for pod_metric in pod_metrics.get('items', []):
                pod_name = pod_metric['metadata']['name']
                namespace = pod_metric['metadata']['namespace']
                
                # Calculate energy consumption
                energy_data = await self._calculate_pod_energy(pod_metric)
                
                if energy_data:
                    energy_kwh = energy_data['energy_kwh']
                    carbon_kg = energy_kwh * carbon_intensity
                    
                    metrics.append({
                        'pod_name': pod_name,
                        'namespace': namespace,
                        'energy_kwh': energy_kwh,
                        'carbon_kg': carbon_kg,
                        'cpu_usage': energy_data['cpu_usage'],
                        'memory_usage': energy_data['memory_usage'],
                        'timestamp': energy_data['timestamp']
                    })
                    
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    async def _calculate_pod_energy(self, pod_metric: Dict) -> Dict:
        """Calculate energy consumption for a single pod"""
        try:
            containers = pod_metric.get('containers', [])
            total_cpu = 0
            total_memory = 0
            
            for container in containers:
                # Parse CPU usage (format: "123n" for nanocores)
                cpu_str = container['usage']['cpu']
                cpu_nanocores = int(cpu_str.rstrip('n'))
                cpu_cores = cpu_nanocores / 1_000_000_000
                
                # Parse memory usage (format: "123Ki")
                memory_str = container['usage']['memory']
                memory_bytes = self._parse_memory(memory_str)
                memory_gb = memory_bytes / (1024**3)
                
                total_cpu += cpu_cores
                total_memory += memory_gb
            
            # Calculate energy consumption
            # CPU energy: CPU cores * TDP * utilization factor
            cpu_tdp = self.cpu_tdp_map['intel']['default']  # Simplified
            cpu_power_watts = total_cpu * cpu_tdp * 0.7  # 70% efficiency factor
            
            # Memory energy: ~3W per GB (DDR4 average)
            memory_power_watts = total_memory * 3
            
            # Total power in kWh (assuming 1-minute measurement interval)
            total_power_kw = (cpu_power_watts + memory_power_watts) / 1000
            energy_kwh = total_power_kw * (1/60)  # 1 minute in hours
            
            return {
                'energy_kwh': energy_kwh,
                'cpu_usage': total_cpu,
                'memory_usage': total_memory,
                'timestamp': pod_metric['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error calculating pod energy: {e}")
            return None
    
    def _parse_memory(self, memory_str: str) -> int:
        """Parse Kubernetes memory format to bytes"""
        if memory_str.endswith('Ki'):
            return int(memory_str[:-2]) * 1024
        elif memory_str.endswith('Mi'):
            return int(memory_str[:-2]) * 1024 * 1024
        elif memory_str.endswith('Gi'):
            return int(memory_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(memory_str)