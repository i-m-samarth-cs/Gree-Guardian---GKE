# setup/generate-load.sh
#!/bin/bash

echo "⚡ Generating load for testing Green Guardian..."

# Port forward Bank of Anthos frontend
kubectl port-forward svc/frontend 8081:80 &
FRONTEND_PID=$!

# Wait for port forward
sleep 5

echo "Generating HTTP load..."

# Simple load generation
for i in {1..100}; do
    curl -s http://localhost:8081 > /dev/null &
    sleep 0.1
done

echo "Load generation complete!"

# Clean up
kill $FRONTEND_PID 2>/dev/null
