######################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the License). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
#####################################################################################################################

import boto3
import copy
import yaml
import os
import shutil

import logs
from execution import exec_command


def create_federated_clusters(config):
    metadata = config.yaml["metadata"]
    [region1, region2] = metadata["regions"]
    zones = [get_availability_zones(region1), get_availability_zones(region2)]

    logs.log(
        f"Deploying federated Amazon EKS clusters in {region1} and {region2}..."
    )

    root_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
    os.chdir(f"{root_path}/cdk-vpc-peering/")
    exec_command(["npm", "install", "--quiet", "--no-progress", "--no-fund"])

    clusters = []
    output_config = dict()
    for idx, region in enumerate(metadata["regions"]):
        cluster_name = f"{metadata['name']}-{idx+1}"
        output_config[f"CLUSTER{idx+1}_NAME"] = cluster_name
        output_config[f"CLUSTER{idx+1}_REGION"] = region
        logs.log(f"Deploying cluster {cluster_name} to {region}")

        eks = boto3.client("eks", region_name=region)
        if cluster_name in eks.list_clusters()["clusters"]:
            raise Exception(f"Cluster \"{cluster_name}\" already exists")

        cluster_template = copy.deepcopy(config.spec)
        cluster_template["metadata"]["name"] = cluster_name
        cluster_template["metadata"]["region"] = region
        cluster_template["vpc"]["cidr"] = get_cidr_for_vpc(idx+1)
        cluster_template["availabilityZones"] = zones[idx]

        cluster_yaml = yaml.dump(cluster_template)

        exec_command(["eksctl", "create", "cluster", "-f", "-"], cluster_yaml)
        cluster_details = eks.describe_cluster(name=cluster_name)["cluster"]
        clusters.append(cluster_details)
        create_identity_mapping(config, region, cluster_details)

    vpc1id = clusters[0]["resourcesVpcConfig"]["vpcId"]
    vpc2id = clusters[1]["resourcesVpcConfig"]["vpcId"]

    logs.log(f"Creating VPC peering")
    bastion = config.bastion
    create_vpc_peering(config, f"{metadata['name']}-peering-clusters",
                               region1, vpc1id, get_cidr_for_vpc(1),
                               region2, vpc2id, get_cidr_for_vpc(2))

    create_vpc_peering(config, f"{metadata['name']}-peering-bastion-{vpc1id}",
                               bastion.region, bastion.vpcid, bastion.vpccidr,
                               region1, vpc1id, get_cidr_for_vpc(1))

    create_vpc_peering(config, f"{metadata['name']}-peering-bastion-{vpc2id}",
                               bastion.region, bastion.vpcid, bastion.vpccidr,
                               region2, vpc2id, get_cidr_for_vpc(2))

    os.chdir("..")
    clusters_disable_public_access(config, clusters)

    logs.log(f"Joining clusters into federation")
    clusters_join_federation(config, clusters)

    output_config["BASE_NAME"] = metadata["name"]
    output_config["BASTION_REGION"] = bastion.region
    write_output_config(config, output_config)

    logs.log("Done. Federated EKS clusters has been created")


def write_output_config(config, output_config):
    metadata = config.yaml["metadata"]
    home_folder = os.path.expanduser("~")
    output_filename = os.path.join(home_folder, f"{metadata['name']}.env")
    lines_array = [f"export {key}={value}\n" for key,
                   value in output_config.items()]

    with open(output_filename, "w") as output_file:
        output_file.writelines(sorted(lines_array))


def get_availability_zones(region):
    ec2 = boto3.client("ec2", region_name=region)
    ec2_zones = ec2.describe_availability_zones()["AvailabilityZones"]
    zones = sorted([val["ZoneName"] for val in ec2_zones])
    return zones[:3]


def get_cidr_for_vpc(index):
    return f"172.2{index}.0.0/16"


def try_remove_files(filenames):
    home_folder = os.path.expanduser("~")

    for filename in filenames:
        filename = filename.replace("~", home_folder)

        try:
            os.remove(filename)
        except FileNotFoundError:
            logs.log(f"[OK] File not found {filename}")


def create_identity_mapping(config, region, cluster):
    if "iamidentitymapping" not in config.yaml:
        return

    mappings = config.yaml["iamidentitymapping"]
    for mapping in mappings:
        exec_command(["eksctl", "create", "iamidentitymapping",
                      "--cluster", cluster["name"], "--region", region,
                      "--arn", mapping["arn"],
                      "--group", mapping["group"],
                      "--username", mapping["username"]
                      ])


def clusters_disable_public_access(config, clusters):
    metadata = config.yaml["metadata"]
    [region1, region2] = metadata["regions"]

    sg1id = clusters[0]["resourcesVpcConfig"]["clusterSecurityGroupId"]
    sg2id = clusters[1]["resourcesVpcConfig"]["clusterSecurityGroupId"]

    ec2 = boto3.client("ec2", region_name=region1)
    ec2.authorize_security_group_ingress(GroupId=sg1id, IpPermissions=[
        {"IpProtocol": "tcp",
         "FromPort": 443,
         "ToPort": 443,
         "IpRanges": [{"CidrIp": get_cidr_for_vpc(0)},
                      {"CidrIp": get_cidr_for_vpc(1)},
                      {"CidrIp": get_cidr_for_vpc(2)}]}
    ])

    ec2 = boto3.client("ec2", region_name=region2)
    ec2.authorize_security_group_ingress(GroupId=sg2id, IpPermissions=[
        {"IpProtocol": "tcp",
         "FromPort": 443,
         "ToPort": 443,
         "IpRanges": [{"CidrIp": get_cidr_for_vpc(0)},
                      {"CidrIp": get_cidr_for_vpc(1)},
                      {"CidrIp": get_cidr_for_vpc(2)}]}
    ])

    exec_command(["eksctl", "utils", "update-cluster-endpoints",
                  f"--cluster={clusters[0]['name']}", f"--region={region1}",
                  "--public-access=false", "--private-access=true",
                  "--approve"])

    exec_command(["eksctl", "utils", "update-cluster-endpoints",
                  f"--cluster={clusters[1]['name']}", f"--region={region2}",
                  "--public-access=false", "--private-access=true",
                  "--approve"])


def clusters_join_federation(config, clusters):
    metadata = config.yaml["metadata"]
    [region1, region2] = metadata["regions"]

    home_folder = os.path.expanduser("~")
    try_remove_files(["~/.kube/config", "~/.kube/config1", "~/.kube/config2"])

    # Setting up kubeconfig for first cluster
    exec_command(["aws", "eks", "--region", region1,
                  "update-kubeconfig", "--name", clusters[0]["name"]])
    shutil.copy(f"{home_folder}/.kube/config", f"{home_folder}/.kube/config1")

    # Provisining Kubefed into primary Amazon EKS  cluster
    exec_command(["./eks-cluster-setup/eks-cluster-install-kubefed.sh"])

    # Setting up kubeconfig for second cluster
    try_remove_files(["~/.kube/config"])
    exec_command(["aws", "eks", "--region", region2,
                  "update-kubeconfig", "--name", clusters[1]["name"]])
    shutil.copy(f"{home_folder}/.kube/config", f"{home_folder}/.kube/config2")

    # Join clusters into federation
    exec_command(["./eks-cluster-setup/eks-cluster-join-fed.sh"])


def create_vpc_peering(config, stack_name, vpc1region, vpc1id, vpc1cidr,
                       vpc2region, vpc2id, vpc2cidr):
    exec_command(["cdk", "deploy",
                  "--require-approval", "never",
                  "-c", f"name={stack_name}-1",
                  "-c", f"vpc1region={vpc1region}",
                  "-c", f"vpc1id={vpc1id}",
                  "-c", f"vpc1cidr={vpc1cidr}",
                  "-c", f"vpc2region={vpc2region}",
                  "-c", f"vpc2id={vpc2id}",
                  "-c", f"vpc2cidr={vpc2cidr}"
                  ])

    cf = boto3.client("cloudformation", region_name=vpc1region)
    stacks = cf.describe_stacks(StackName=f"{stack_name}-1")["Stacks"]

    peeringConnectionId = ""
    for stack in stacks:
        for output in stack["Outputs"]:
            if "PeeringConnectionId" in output["OutputKey"]:
                peeringConnectionId = output["OutputValue"]
                break

    exec_command(["cdk", "deploy",
                  "--require-approval", "never",
                  "-c", f"peeringConnectionId={peeringConnectionId}",
                  "-c", f"name={stack_name}-2",
                  "-c", f"vpc1region={vpc2region}",
                  "-c", f"vpc1id={vpc2id}",
                  "-c", f"vpc1cidr={vpc2cidr}",
                  "-c", f"vpc2region={vpc1region}",
                  "-c", f"vpc2id={vpc1id}",
                  "-c", f"vpc2cidr={vpc1cidr}"
                  ])
