#!/bin/bash
set -ex

ReplaceAndLowerTheKubeConfig() {
    local file=$1

    local searchServer=$(kubectl config view -o json | jq -c '.clusters[] | select (.name) | .name' | jq -r .)
    local replaceServer=$(kubectl config view -o json | jq -c '.clusters[] | select (.name) | .name | sub(".*/";"")' | jq -r .)
    local serverURL=$(kubectl config view -o json | jq -c '.clusters[] | select (.name) | .cluster.server' | jq -r .)

    echo 'search server: ' ${searchServer}
    echo 'replaceServer: ' ${replaceServer}

    if [ ${#searchServer} -gt 0 ]; then
        echo 'Found Cluster name and it will be shortened'
    else
        echo 'Cluster name is empty or null in kubeconfig file'
        exit
    fi

    if [ ${#serverURL} -gt 4 ]; then
        echo 'Server URL found and would be lowered'
    else
        echo 'Cluster URL is empty or null in kubeconfig file'
        exit
    fi

    local lowerServerURL=$(echo "$serverURL" | tr '[:upper:]' '[:lower:]')

    local lowerReplaceServer=$(echo "$replaceServer" | tr '[:upper:]' '[:lower:]')

    # Replacing cluster name
    sed -i "s!${searchServer}!${lowerReplaceServer}!g" "$file"

    # Lowering cluster URLs
    sed -i "s!${serverURL}!${lowerServerURL}!g" "$file"
}

cat ~/.kube/config1 >~/.kube/config
ReplaceAndLowerTheKubeConfig ~/.kube/config1
cat ~/.kube/config2 >~/.kube/config
ReplaceAndLowerTheKubeConfig ~/.kube/config2

# Merge 2 configs into one
KUBECONFIG=~/.kube/config1:~/.kube/config2 kubectl config view --flatten >~/.kube/config

kubeFed1_CTX=$(kubectl config view -o json | jq -c '.contexts[0] | select (.name) | .name' | jq -r .)
echo "kubeFed1_CTX:$kubeFed1_CTX"
kubeFed2_CTX=$(kubectl config view -o json | jq -c '.contexts[1] | select (.name) | .name' | jq -r .)
echo "kubeFed2_CTX:$kubeFed2_CTX"

kubeFed1_clustername=$(kubectl config view -o json | jq -c '.clusters[0] | select (.name) | .name' | jq -r .)
echo "kubeFed1_clustername:$kubeFed1_clustername"
kubeFed2_clustername=$(kubectl config view -o json | jq -c '.clusters[1] | select (.name) | .name' | jq -r .)
echo "kubeFed2_clustername:$kubeFed2_clustername"

kubefedctl join $kubeFed1_clustername --cluster-context $kubeFed1_CTX --host-cluster-context $kubeFed1_CTX --v=2
kubefedctl join $kubeFed2_clustername --cluster-context $kubeFed2_CTX --host-cluster-context $kubeFed1_CTX --v=2

# Show federated clusters
kubectl -n kube-federation-system get kubefedclusters
