#!/bin/bash

# step 1 -> delete peering
for region in $CLUSTER1_REGION $CLUSTER2_REGION $BASTION_REGION; do
    for stack_name in $(aws cloudformation describe-stacks --region $region | jq '.Stacks[].StackName' | jq -r . | grep "$BASE_NAME-peering"); do
        echo "Step 1: deleting $stack_name stack in region: $region"
        aws cloudformation delete-stack --stack-name $stack_name --region $region
    done
done

# step 2: delete node groups (need to wait before deleting clusters)
for region in $CLUSTER1_REGION $CLUSTER2_REGION; do
    for stack_name in $(aws cloudformation describe-stacks --region $region | jq '.Stacks[].StackName' | jq -r . | grep "$BASE_NAME-.*nodegroup"); do
        echo "Step 2: deleting $stack_name stack in region: $region"
        aws cloudformation delete-stack --stack-name $stack_name --region $region
        status=0
        while [ $status -eq 0 ]; do # wait nodegroup stacks being deleted fully
            sleep 10
            aws cloudformation describe-stacks --stack-name $stack_name --region $region >/dev/null 2>&1
            status=$?
        done
    done
done

# step 3 delete cluster
for region in $CLUSTER1_REGION $CLUSTER2_REGION; do
    echo "$region"
    for stack_name in $(aws cloudformation describe-stacks --region $region | jq '.Stacks[].StackName' | jq -r . | grep "$BASE_NAME-.*cluster"); do
        echo "Step 3: deleting $stack_name stack in region: $region"
        aws cloudformation delete-stack --stack-name $stack_name --region $region
        status=0
        while [ $status -eq 0 ]; do
            sleep 10
            aws cloudformation describe-stacks --stack-name $stack_name --region $region >/dev/null 2>&1
            status=$?
        done
    done
done

echo "All resoruces: VPC Peering, EKS NodeGroups and EKS clusters were deleted."
