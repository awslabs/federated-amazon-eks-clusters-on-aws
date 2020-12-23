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

import { Construct, StackProps, CfnOutput } from "@aws-cdk/core";
import { Vpc, CfnVPCPeeringConnection, CfnRoute } from "@aws-cdk/aws-ec2";
import { VpcStub } from "./vpc-stub";

export interface VpcPeeringConstructProps extends StackProps {
    name: string,
    vpc1: VpcStub;
    vpc2: VpcStub;
    peeringConnectionId?: string;
}

export class VpcPeeringConstruct extends Construct {
    constructor(scope: Construct, id: string, props: VpcPeeringConstructProps) {
        super(scope, id);

        const { name, vpc1, vpc2 } = props;

        console.log(`Setting up peering: ${vpc1.id} / ${vpc2.id}`);
        let peeringConnectionId = props.peeringConnectionId;

        if (peeringConnectionId === undefined) {
            const peeringConnection = new CfnVPCPeeringConnection(this,
                `peering-${vpc1.id}-${vpc2.id}`,
                {
                    vpcId: vpc1.id,
                    peerVpcId: vpc2.id,
                    peerRegion: vpc2.region,
                    tags: [{ key: "Name", value: name }]
                }
            );

            peeringConnectionId = peeringConnection.ref;
        }

        const sourceVpc = Vpc.fromLookup(this, vpc1.id, {
            vpcId: vpc1.id
        });

        let routeTableIds = [];
        for (const subnet of [...sourceVpc.publicSubnets, ...sourceVpc.privateSubnets]) {
            routeTableIds.push(subnet.routeTable.routeTableId);
        }

        let i = 0;
        routeTableIds = [...new Set(routeTableIds)];
        for (const routeTableId of routeTableIds) {
            new CfnRoute(this, `${name}-${i++}`, {
                routeTableId,
                destinationCidrBlock: vpc2.cidr,
                vpcPeeringConnectionId: peeringConnectionId
            });
        }

        const exportName = `${vpc1.id}-${vpc2.id}-PeeringConnectionId`
        new CfnOutput(this, exportName, {
            exportName,
            description: "PeeringConnectionId",
            value: peeringConnectionId || "None"
        });
    }
}