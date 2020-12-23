/*********************************************************************************************************************
 *  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                    *
 *                                                                                                                    *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import { App, Stack } from "@aws-cdk/core";
import { VpcPeeringConstruct } from "./vpc-peering-construct";

const app = new App();
const node = app.node;

const name = node.tryGetContext("name");
const peeringConnectionId = node.tryGetContext("peeringConnectionId");

const vpc1id = node.tryGetContext("vpc1id");
const vpc1region = node.tryGetContext("vpc1region");
const vpc1cidr = node.tryGetContext("vpc1cidr");

const vpc2id = node.tryGetContext("vpc2id");
const vpc2region = node.tryGetContext("vpc2region");
const vpc2cidr = node.tryGetContext("vpc2cidr");

const stack = new Stack(app, name, {
    env: {
        account: process.env.CDK_DEFAULT_ACCOUNT,
        region: vpc1region
    }
});

new VpcPeeringConstruct(stack, name, {
    peeringConnectionId: peeringConnectionId,
    name,
    vpc1: {
        id: vpc1id,
        region: vpc1region,
        cidr: vpc1cidr
    },
    vpc2: {
        id: vpc2id,
        region: vpc2region,
        cidr: vpc2cidr
    }
});