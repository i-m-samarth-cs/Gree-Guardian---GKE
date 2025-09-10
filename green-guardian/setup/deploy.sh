# setup/deploy.sh
#!/bin/bash

echo "🚀 Deploying Green Guardian..."

# Create namespace
kubectl apply -f k8s/namespace.yaml

# Check if Gemini secret exists
if ! kubectl get secret gemini-secret -n green-guardian &> /dev/null; then
    echo "⚠️  Gemini API secret not found!"
    echo "Please create it with: kubectl create secret generic gemini-secret --from-literal=api-key=YOUR_GEMINI_API_KEY -n green-guardian"
    read -p "Enter your Gemini API key: " api_key
    kubectl create secret generic gemini-secret --from-literal=api-key="$api_key" -n green-guardian
fi

# Deploy monitoring stack
echo "Deploying Prometheus..."
kubectl apply -f k8s/monitoring-stack.yaml

# Wait for Prometheus to be ready
echo "Waiting for Prometheus to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n green-guardian

# Deploy Green Guardian components
echo "Deploying Green Guardian agent..."
kubectl apply -f k8s/agent-deployment.yaml

echo "Deploying Green Guardian dashboard..."
kubectl apply -f k8s/dashboard-deployment.yaml

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/green-guardian-dashboard -n green-guardian

echo "✅ Green Guardian deployed successfully!"
echo ""
echo "📊 Access the dashboard:"
echo "   kubectl port-forward svc/green-guardian-dashboard 8080:80 -n green-guardian"
echo "   Then open: http://localhost:8080"
echo ""
echo "📈 Access Prometheus (optional):"
echo "   kubectl port-forward svc/prometheus 9090:9090 -n green-guardian"
echo "   Then open: http://localhost:9090"
