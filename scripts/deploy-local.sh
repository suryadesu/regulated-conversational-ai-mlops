#!/usr/bin/env bash
# Build the three service images, load them into kind, and apply the local
# kustomize overlay; wait for the gateway Rollout to become healthy.
set -euo pipefail

CLUSTER_NAME="${KIND_CLUSTER_NAME:-regulated-conv-ai}"

docker build -t gateway:local -f services/gateway/Dockerfile .
docker build -t provider-stub:local -f services/provider-stub/Dockerfile .
docker build -t ticket-worker:local -f services/ticket-worker/Dockerfile .

kind load docker-image gateway:local provider-stub:local ticket-worker:local \
  --name "$CLUSTER_NAME"

kubectl apply -k deploy/k8s/overlays/local

kubectl argo rollouts status gateway -n default --timeout 180s \
  || kubectl get rollout gateway -n default -o wide

echo "local overlay applied."
