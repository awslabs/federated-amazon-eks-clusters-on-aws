#!/bin/bash

set -ex

BASE_DIR=$(dirname $0)

# create test NS
kubectl apply -f $BASE_DIR/namespace.yaml
kubectl apply -f $BASE_DIR/federated-namespace.yaml
kubectl apply -f $BASE_DIR/federated-nginx.yaml
# Replicas scheduling preference across Fed EKS clusters
kubectl apply -f $BASE_DIR/federated-deployment-rsp.yaml
