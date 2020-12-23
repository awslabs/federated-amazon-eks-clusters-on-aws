#!/usr/bin/env python3

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

import argparse
import signal
import sys

import logs
import create_action
import destroy_action
from errors import ArgumentError


def main():
    parser = argparse.ArgumentParser(
        prog="eksfedctl", description="Amazon EKS Federated Clusters")
    parser.version = "1.0.5"

    parser.add_argument("-v", "--version", action="version")
    subparsers = parser.add_subparsers(title="commands")

    create_parser = subparsers.add_parser(
        "create", help="create Amazon EKS federated clusters")
    create_parser.set_defaults(
        parser=create_parser,
        func=create_action.process)
    create_parser.add_argument(
        "-f", "--file", type=str, help="load configuration from a file")
    create_parser.add_argument(
        "-n", "--name", type=str, help="cluster name")
    create_parser.add_argument(
        "-r", "--regions", nargs=2, type=str, help="cluster regions")
    create_parser.add_argument(
        "-d", "--dry-run", action="store_true", help="dry run")

    destroy_parser = subparsers.add_parser(
        "destroy", help="destroy Amazon EKS federated clusters")
    destroy_parser.set_defaults(
        parser=destroy_parser,
        func=destroy_action.process)
    destroy_parser.add_argument(
        "-f", "--file", type=str, required=True,
        help="load configuration from a file")

    args = parser.parse_args()
    if "func" not in args:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except ArgumentError as argument_error:
        error(argument_error, args.parser)
    except Exception as ex:
        error(ex)


def error(message, parser=None):
    logs.error(message)

    if parser:
        print("")
        parser.print_help()

    sys.exit(1)


def interrupt_signal_handler(sig, frame):
    print("Interrupting and exit!")
    sys.exit(1)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, interrupt_signal_handler)

    main()
