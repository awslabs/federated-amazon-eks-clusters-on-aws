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

import { Stack } from '@aws-cdk/core';
import { expect, countResourcesLike, haveResource } from '@aws-cdk/assert';
import { Vpc } from "@aws-cdk/aws-ec2";
import * as vpcpeering from '../src/vpc-peering-construct'

const name = "testName";
const vpc1 = {
    id: '123',
    cidr: '172.30.0.0/16',
    region: "eu-west-1"
};
const vpc2 = {
    id: '333',
    cidr: '172.31.0.0/16',
    region: "eu-central-1"
};

const testenv = { env: { region: 'eu-west-1', account: Math.random().toString().substring(2, 14) } };
var stack: Stack;

function initStack() {
    stack = new Stack(undefined, undefined, testenv);
}

beforeEach(() => {
    initStack();
});

test('vpcpeering creates peering construct', () => {
    new vpcpeering.VpcPeeringConstruct(stack, 'Peering', {
        name: name,
        vpc1: vpc1,
        vpc2: vpc2
    });
    //Testing the fact that Peering connection resource is created
    expect(stack).to(haveResource('AWS::EC2::VPCPeeringConnection', {
        VpcId: vpc1.id,
        PeerVpcId: vpc2.id,
        PeerRegion: vpc2.region,
        Tags: [
            {
                Key: "Name",
                Value: name
            }
        ],
    }));
});

test('vpcpeering creates route tables', () => {
    new vpcpeering.VpcPeeringConstruct(stack, 'Peering', {
        name: name,
        vpc1: vpc1,
        vpc2: vpc2
    });
    //Testing the fact that Peering connection resource is created
    expect(stack).to(haveResource('AWS::EC2::Route', {
        DestinationCidrBlock: vpc2.cidr
    }));
});

test('peering connection id is used when provided', () => {
    const peeringConnectionId = "peer-123";
    new vpcpeering.VpcPeeringConstruct(stack, 'Peering', {
        name: name,
        vpc1: vpc1,
        vpc2: vpc2,
        peeringConnectionId: peeringConnectionId
    });

    //Testing the fact that Peering connection resource is created
    expect(stack).to(haveResource('AWS::EC2::Route', {
        VpcPeeringConnectionId: peeringConnectionId
    }));
});

test('vpcpeering creates dynamic routes', () => {
    new vpcpeering.VpcPeeringConstruct(stack, 'Peering', {
        name: name,
        vpc1: vpc1,
        vpc2: vpc2
    });

    const sourceVpc = Vpc.fromLookup(stack, vpc1.id, { vpcId: vpc1.id });
    const numSubnets = sourceVpc.publicSubnets.length + sourceVpc.privateSubnets.length;

    //Testing dynamic routes. Check that route has been created for every subnet
    expect(stack).to(countResourcesLike('AWS::EC2::Route', numSubnets, {
        DestinationCidrBlock: vpc2.cidr
    }));
});