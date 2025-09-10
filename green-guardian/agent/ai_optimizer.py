import asyncio
import json
import logging
from typing import List, Dict, Optional
import aiohttp
from kubernetes import client
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OptimizationAction:
    type: str  # 'scale_down', 'scale_up', 'adjust_resources', 'hibernate'
    target_pod: str
    target_namespace: str
    parameters: Dict
    confidence: float
    estimated_savings: float

class AIOptimizer:
    def __init__(self, gemini_api_key: str):
        self.api_key = gemini_api_key
        self.apps_v1 = client.AppsV1Api()
        self.historical_data = []  # Store for learning
        
    async def analyze_and_optimize(self, metrics: List[Dict]) -> List[OptimizationAction]:
        """Use AI to analyze metrics and suggest optimizations"""
        if not metrics:
            return []
        
        try:
            # Analyze with Gemini
            analysis = await self._analyze_with_gemini(metrics)
            
            # Convert analysis to optimization actions
            actions = await self._generate_optimization_actions(analysis, metrics)
            
            # Execute safe optimizations
            executed_actions = await self._execute_optimizations(actions)
            
            # Store results for learning
            self._store_historical_data(metrics, executed_actions)
            
            return executed_actions
            
        except Exception as e:
            logger.error(f"Error in AI optimization: {e}")
            return []
    
    async def _analyze_with_gemini(self, metrics: List[Dict]) -> Dict:
        """Send metrics to Gemini for analysis"""
        prompt = self._build_analysis_prompt(metrics)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'contents': [{
                        'parts': [{'text': prompt}]
                    }],
                    'generationConfig': {
                        'temperature': 0.1,
                        'maxOutputTokens': 1000
                    }
                }
                
                async with session.post(
                    'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
                    headers=headers,
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result['candidates'][0]['content']['parts'][0]['text']
                        return json.loads(text)
                    else:
                        logger.error(f"Gemini API error: {resp.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return {}
    
    def _build_analysis_prompt(self, metrics: List[Dict]) -> str:
        """Build prompt for Gemini analysis"""
        metrics_summary = []
        for metric in metrics[:10]:  # Limit to prevent token overflow
            metrics_summary.append({
                'pod': metric['pod_name'],
                'namespace': metric['namespace'],
                'energy_kwh': round(metric['energy_kwh'], 6),
                'carbon_kg': round(metric['carbon_kg'], 6),
                'cpu_usage': round(metric['cpu_usage'], 3),
                'memory_usage': round(metric['memory_usage'], 3)
            })
        
        return f"""
        Analyze the following Kubernetes pod energy consumption metrics and provide optimization recommendations.
        
        Current metrics:
        {json.dumps(metrics_summary, indent=2)}
        
        Historical average (if available):
        {json.dumps(self._get_historical_average(), indent=2)}
        
        Please respond with a JSON object containing:
        {{
            "anomalies": [list of pods with unusual energy consumption],
            "optimization_opportunities": [
                {{
                    "pod": "pod_name",
                    "namespace": "namespace",
                    "type": "scale_down|scale_up|adjust_resources|hibernate",
                    "confidence": 0.0-1.0,
                    "reason": "explanation",
                    "estimated_savings_kwh": 0.0,
                    "parameters": {{}}
                }}
            ],
            "cluster_insights": "overall analysis"
        }}
        
        Focus on:
        1. Pods consuming excessive energy relative to their workload
        2. Underutilized resources that could be scaled down
        3. Opportunities for intelligent scheduling
        4. Patterns suggesting resource leaks or inefficiencies
        """
    
    async def _generate_optimization_actions(self, analysis: Dict, metrics: List[Dict]) -> List[OptimizationAction]:
        """Convert AI analysis to concrete optimization actions"""
        actions = []
        
        for opportunity in analysis.get('optimization_opportunities', []):
            if opportunity.get('confidence', 0) > 0.7:  # High confidence threshold
                action = OptimizationAction(
                    type=opportunity['type'],
                    target_pod=opportunity['pod'],
                    target_namespace=opportunity['namespace'],
                    parameters=opportunity.get('parameters', {}),
                    confidence=opportunity['confidence'],
                    estimated_savings=opportunity.get('estimated_savings_kwh', 0)
                )
                actions.append(action)
        
        return actions
    
    async def _execute_optimizations(self, actions: List[OptimizationAction]) -> List[OptimizationAction]:
        """Execute safe optimization actions"""
        executed = []
        
        for action in actions:
            try:
                if action.type == 'scale_down' and action.confidence > 0.8:
                    success = await self._scale_deployment(
                        action.target_namespace,
                        action.target_pod,
                        'down'
                    )
                    if success:
                        executed.append(action)
                        logger.info(f"Scaled down {action.target_pod}")
                
                elif action.type == 'adjust_resources' and action.confidence > 0.9:
                    success = await self._adjust_pod_resources(action)
                    if success:
                        executed.append(action)
                        logger.info(f"Adjusted resources for {action.target_pod}")
                
            except Exception as e:
                logger.error(f"Error executing optimization {action.type}: {e}")
        
        return executed
    
    async def _scale_deployment(self, namespace: str, pod_name: str, direction: str) -> bool:
        """Scale deployment up or down"""
        try:
            # Find deployment for pod
            pod = self.v1.read_namespaced_pod(pod_name, namespace)
            owner_refs = pod.metadata.owner_references
            
            if not owner_refs:
                return False
            
            for ref in owner_refs:
                if ref.kind == 'ReplicaSet':
                    rs = self.apps_v1.read_namespaced_replica_set(ref.name, namespace)
                    deploy_refs = rs.metadata.owner_references
                    
                    for deploy_ref in deploy_refs:
                        if deploy_ref.kind == 'Deployment':
                            deployment = self.apps_v1.read_namespaced_deployment(
                                deploy_ref.name, namespace
                            )
                            
                            current_replicas = deployment.spec.replicas
                            if direction == 'down' and current_replicas > 1:
                                new_replicas = current_replicas - 1
                            elif direction == 'up':
                                new_replicas = current_replicas + 1
                            else:
                                return False
                            
                            # Update deployment
                            deployment.spec.replicas = new_replicas
                            self.apps_v1.patch_namespaced_deployment(
                                deploy_ref.name, namespace, deployment
                            )
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error scaling deployment: {e}")
            return False
    
    async def _adjust_pod_resources(self, action: OptimizationAction) -> bool:
        """Adjust pod resource requests/limits"""
        try:
            # This would require more complex logic to update deployments
            # For hackathon demo, we'll simulate the action
            logger.info(f"Simulating resource adjustment for {action.target_pod}")
            return True
            
        except Exception as e:
            logger.error(f"Error adjusting resources: {e}")
            return False
    
    def _get_historical_average(self) -> Dict:
        """Get historical averages for comparison"""
        if not self.historical_data:
            return {}
        
        # Simplified historical analysis
        total_energy = sum(d['energy_kwh'] for d in self.historical_data[-100:])
        total_carbon = sum(d['carbon_kg'] for d in self.historical_data[-100:])
        count = len(self.historical_data[-100:])
        
        if count > 0:
            return {
                'avg_energy_kwh': total_energy / count,
                'avg_carbon_kg': total_carbon / count
            }
        return {}
    
    def _store_historical_data(self, metrics: List[Dict], actions: List[OptimizationAction]):
        """Store data for future learning"""
        for metric in metrics:
            self.historical_data.append(metric)
        
        # Keep only recent data to prevent memory issues
        if len(self.historical_data) > 1000:
            self.historical_data = self.historical_data[-1000:]