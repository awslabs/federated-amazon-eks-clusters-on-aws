#!/bin/bash
set -ex

helm repo add kubefed-charts https://raw.githubusercontent.com/kubernetes-sigs/kubefed/master/charts
helm search repo kubefed
helm --namespace kube-federation-system upgrade -i kubefed kubefed-charts/kubefed --version=0.5.1 --create-namespace
kubectl wait --for=condition=available --timeout=120s --all deployments -n kube-federation-system
