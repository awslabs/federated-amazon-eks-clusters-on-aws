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
import yaml
import json
import types
import requests
import uuid
import re
import sys
import os

from create_script import create_federated_clusters
from errors import ArgumentError


def process(args):
    check_tmux_session()

    config = get_config(args)
    validate_config(config)

    if not args.dry_run:
        create_federated_clusters(config)
    else:
        dump_config(config)


def check_tmux_session():
    msg_head = "Federation creation should be launched inside tmux session"
    msg_command = "run \"tmux\" or \"tmux attach\" to start new session or attach to existing one"

    if "TMUX" not in os.environ:
        raise Exception(f"{msg_head}\n{msg_command}")


def dump_config(config):
    print(yaml.dump(vars(config.bastion)))
    print("---\n")
    print(yaml.dump(config.yaml))
    print("---\n")
    print(yaml.dump(config.spec))


def get_config(args):
    config = types.SimpleNamespace()
    config.bastion = get_instance_metadata()
    config_yaml = {"metadata": {}}
    config_spec = {"metadata": {}}

    # 1. Default template
    root_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
    default_yaml_path = os.path.join(root_path, "default.yaml")
    default_yaml = load_yaml(default_yaml_path)
    default_spec = default_yaml["spec"]
    del default_yaml["spec"]
    config_yaml = {**config_yaml, **default_yaml}
    config_spec = {**config_spec, **default_spec}

    # 2. User-provided template
    if args.file:
        # Remove default nodeGroups and managedNodeGroups form the config
        if "managedNodeGroups" in config_spec:
            del config_spec["managedNodeGroups"]
        if "nodeGroups" in config_spec:
            del config_spec["nodeGroups"]

        user_yaml = load_yaml(args.file)
        validate_user_yaml(user_yaml)

        if "spec" in user_yaml:
            user_spec = user_yaml["spec"]
            del user_yaml["spec"]
            config_spec = {**config_spec, **user_spec}

        config_yaml = {**config_yaml, **user_yaml}

    # 3. Command-line arguments
    if args.name:
        config_yaml["metadata"]["name"] = args.name
    if args.regions:
        config_yaml["metadata"]["regions"] = args.regions

    if "name" not in config_yaml["metadata"] or not config_yaml["metadata"]["name"]:
        config_yaml["metadata"]["name"] = f"eksfed-{uuid.uuid4().hex[0:6]}"

    if "regions" not in config_yaml["metadata"]:
        config_yaml["metadata"]["regions"] = []

    config.yaml = config_yaml
    config.spec = config_spec

    return config


def validate_config(config):
    metadata = config.yaml["metadata"]

    if not re.match("^[-A-Za-z0-9]{1,63}$", metadata["name"]):
        raise Exception(
            "Name must be at least 1 character in length letters and numbers"
        )

    if len(metadata["regions"]) != 2:
        raise ArgumentError("Please specify exactly 2 regions")

    ec2 = boto3.client("ec2", region_name=config.bastion.region)
    ec2_regions = ec2.describe_regions()["Regions"]
    region_names = [val["RegionName"] for val in ec2_regions]

    for region in metadata["regions"]:
        # Checking region validity first for faster response
        if not region in region_names:
            raise Exception(f"Region \"{region}\" is not valid")

        try:
            eks = boto3.client("eks", region_name=region)
            eks.list_clusters()
        except Exception as ex:
            raise Exception(f"Can't access EKS service in \"{region}\"")


def validate_user_yaml(input_yaml):
    keys = ["apiVersion", "kind", "metadata", "iamidentitymapping", "spec"]
    for key in input_yaml:
        if key not in keys:
            raise Exception(f"Unknown key \"{key}\"")

    if "apiVersion" not in input_yaml:
        raise Exception("Property \"apiVersion\" not found in yaml")
    elif input_yaml["apiVersion"] != "fedk8s/v1":
        raise Exception(f"Unknown \"apiVersion\": {input_yaml['apiVersion']}")

    if "kind" not in input_yaml:
        raise Exception("Property \"kind\" not found in yaml")
    elif input_yaml["kind"] != "FederatedEKSConfig":
        raise Exception(f"Unknown \"kind\": {input_yaml['kind']}")

    if "metadata" not in input_yaml:
        raise Exception("Property \"metadata\" not found in yaml")

    if "spec" in input_yaml:
        # Supported subset of eksctl.io/v1alpha5
        spec_keys = ["iam", "nodeGroups", "managedNodeGroups",
                     "fargateProfiles", "git", "cloudWatch"]

        supported_keys_str = f"Supported keys are: {', '.join(spec_keys)}"
        for spec_key in input_yaml["spec"]:
            if spec_key not in spec_keys:

                raise Exception(
                    f"Unknown key \"spec.{spec_key}\" {supported_keys_str}"
                )


def load_yaml(file_name):
    if file_name == "-":
        try:
            #config = yaml.load(sys.stdin, Loader=yaml.FullLoader)
            config = yaml.safe_load(sys.stdin)
            return config
        except yaml.YAMLError as exc:
            raise Exception(f"Error in configuration file: {exc}")
    else:
        home_folder = os.path.expanduser("~")
        file_name = file_name.replace("~", home_folder)

        try:
            with open(file_name, "r") as file:
                try:
                    #config = yaml.load(file, Loader=yaml.FullLoader)
                    config = yaml.safe_load(sys.stdin)
                    return config
                except yaml.YAMLError as exc:
                    raise Exception(f"Error in configuration file: {exc}")
        except IOError as e:
            raise Exception(e)


def get_instance_metadata():
    metadata = types.SimpleNamespace()
    base_url = "http://169.254.169.254/latest"

    identity = json.loads(requests.get(
        f"{base_url}/dynamic/instance-identity/document"
    ).text)

    metadata.region = identity["region"]

    metadata.network_interface = requests.get(
        f"{base_url}/meta-data/network/interfaces/macs/"
    ).text

    metadata.vpcid = requests.get(
        f"{base_url}/meta-data/network/interfaces/macs/{metadata.network_interface}/vpc-id/"
    ).text

    metadata.vpccidr = requests.get(
        f"{base_url}/meta-data/network/interfaces/macs/{metadata.network_interface}/vpc-ipv4-cidr-block/"
    ).text

    return metadata
