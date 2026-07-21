#!/usr/bin/env bash
# Create the local kind cluster and install the platform operators:
# KEDA (autoscaling), Argo Rollouts (canary), kube-prometheus-stack (metrics).
set -euo pipefail

CLUSTER_NAME="${KIND_CLUSTER_NAME:-regulated-conv-ai}"

kind create cluster --name "$CLUSTER_NAME" --wait 120s

helm repo add kedacore https://kedacore.github.io/charts
helm repo add argo https://argoproj.github.io/argo-helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install keda kedacore/keda --namespace keda --create-namespace --wait
helm install argo-rollouts argo/argo-rollouts --namespace argo-rollouts --create-namespace --wait
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace --wait --timeout 10m

echo "cluster '$CLUSTER_NAME' ready with KEDA, Argo Rollouts, kube-prometheus-stack."
echo "NOTE: the 'kubectl argo rollouts' plugin is required for promote/abort:"
echo "  curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64"
echo "  chmod +x kubectl-argo-rollouts-linux-amd64 && sudo mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts"
