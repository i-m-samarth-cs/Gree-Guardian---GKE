# setup/install-bank-of-anthos.sh
#!/bin/bash

echo "🏪 Installing Bank of Anthos for testing..."

# Clone Bank of Anthos
if [ ! -d "bank-of-anthos" ]; then
    git clone https://github.com/GoogleCloudPlatform/bank-of-anthos.git
fi

cd bank-of-anthos

# Install Bank of Anthos
kubectl apply -f ./kubernetes-manifests

# Wait for deployment
echo "Waiting for Bank of Anthos to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n default

echo "✅ Bank of Anthos installed!"
echo "🌐 Access it with: kubectl port-forward svc/frontend 8081:80"

cd ..