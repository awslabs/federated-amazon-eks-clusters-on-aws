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

import sys
import os
from execution import exec_command


def process(args):
    if not confirm_destroy():
        sys.exit()

    home_folder = os.path.expanduser("~")
    config_filename = args.file.replace("~", home_folder)
    root_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

    exec_command(
        ["bash", "-c",
         f"source '{config_filename}' && bash '{root_path}/eks-cluster-setup/eks-cluster-destroy.sh'"]
    )


def confirm_destroy():
    question = "Do you want to destroy federated EKS clusters? [y/N]: "
    answer = ""

    while answer not in ["y", "n"]:
        answer = str(input(question)).lower().strip()
        if answer == "":
            return False

    return answer == "y"
