# setup/cleanup.sh
#!/bin/bash

echo "🧹 Cleaning up Green Guardian..."

# Remove Green Guardian resources
kubectl delete -f k8s/ --ignore-not-found=true

# Remove namespace (this will delete everything in it)
kubectl delete namespace green-guardian --ignore-not-found=true

# Optional: Clean up Bank of Anthos
read -p "Do you want to remove Bank of Anthos as well? (y/N): " cleanup_boa
if [[ $cleanup_boa =~ ^[Yy]$ ]]; then
    if [ -d "bank-of-anthos" ]; then
        kubectl delete -f ./bank-of-anthos/kubernetes-manifests --ignore-not-found=true
        rm -rf bank-of-anthos
    fi
fi

echo "✅ Cleanup complete!"
