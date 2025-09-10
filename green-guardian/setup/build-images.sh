# setup/build-images.sh
#!/bin/bash

echo "🏗️  Building Green Guardian Docker Images..."

# Build agent image
echo "Building agent image..."
docker build -f docker/Dockerfile.agent -t green-guardian-agent:latest .

# Build dashboard image
echo "Building dashboard image..."
docker build -f docker/Dockerfile.dashboard -t green-guardian-dashboard:latest .

echo "✅ Images built successfully!"
echo "📋 Next steps:"
echo "   1. Create Gemini API secret: kubectl create secret generic gemini-secret --from-literal=api-key=YOUR_GEMINI_API_KEY -n green-guardian"
echo "   2. Deploy: kubectl apply -f k8s/"
echo "   3. Port forward: kubectl port-forward svc/green-guardian-dashboard 8080:80 -n green-guardian"
