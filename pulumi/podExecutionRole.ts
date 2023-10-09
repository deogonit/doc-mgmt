import * as aws from '@pulumi/aws'
import * as pulumi from '@pulumi/pulumi'
import { accountId, region, project, stack } from "./globals";
import { IamRole } from './iamRoleComponent';
import { IamPolicy } from './iamPolicyComponent';
import {
    DocumentsArn,
    EnvelopeCallbacksArn,
    EnvelopesArn,
    bucketArn,
    templatesBucketArn,
} from "./stackRefs";

const config = new pulumi.Config(project);
const s3AccessTo = config.requireObject("s3AccessTo");
const eksClusterName = config.require("eksClusterName");
const namespace = config.require("namespace");
const vClusterNamespace = stack == "prod" ? "" : config.require('vClusterNamespace');

const cluster = aws.eks.getClusterOutput({
    name: eksClusterName,
});

const tags = {
    project: project,
    environment: stack,
}

const podExecutionPolicy = new IamPolicy(`${stack}-${project}-pod-execution-policy`, {
    path: "/",
    description: `${stack}-${project}-pod-execution-policy`,
    listOfStatements: pulumi.jsonStringify({
        Version: "2012-10-17",
        Statement: [
            {
                Sid: "AccessTable",
                Effect: "Allow",
                Action: [
                    "dynamodb:*"
                ],
                Resource: [
                    pulumi.interpolate`${DocumentsArn}`,
                    pulumi.interpolate`${EnvelopeCallbacksArn}`,
                    pulumi.interpolate`${EnvelopesArn}`,
                ]
            },
            {
                Action: "*",
                Effect: "Allow",
                Resource: [
                    pulumi.interpolate`${bucketArn}`,
                    pulumi.interpolate`${bucketArn}/*`,
                ]
            },
            {

                Action: [
                    "s3:ListBucket",
                    "s3:GetBucketAcl",
                    "s3:GetBucketLocation",
                    "s3:GetBucketPolicyStatus",
                    "s3:GetBucketPublicAccessBlock",
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                ],
                Effect: "Allow",
                Resource: [
                    pulumi.interpolate`${templatesBucketArn}`,
                    pulumi.interpolate`${templatesBucketArn}/*`,
                ],
                Sid: "TemplatesReadOnly"
            },
            {
                Action: "*",
                Effect: "Allow",
                Resource: s3AccessTo
            }
        ]
    }),
    tags: tags,
});

const k8sSaName = stack == "prod" ? `system:serviceaccount:${namespace}:${namespace}-sa` :
    `system:serviceaccount:${vClusterNamespace}:${namespace}-sa-x-${namespace}-x-${vClusterNamespace}`;

const saAssumeRolePolicy = pulumi
    .all([cluster.identities[0].oidcs[0].issuer, accountId])
    .apply(([identityUrl, accountId]) =>
        aws.iam.getPolicyDocument({
            statements: [
                {
                    actions: ['sts:AssumeRoleWithWebIdentity'],
                    conditions: [
                        {
                            test: 'StringEquals',
                            values: [`${k8sSaName}`],
                            variable: `${identityUrl.replace('https://', '')}:sub`,
                        },
                    ],
                    effect: 'Allow',
                    principals: [{
                        identifiers: [`arn:aws:iam::${accountId}:oidc-provider/${identityUrl.replace('https://', '')}`],
                        type: 'Federated'
                    }],
                },
            ],
        })
    );

// Create a new IAM role that assumes the AssumeRoleWebWebIdentity policy.
const saRole = new IamRole(`${stack}-${project}-eks-pod-execution-role`, {
    assumeRolePolicy: saAssumeRolePolicy.json,
    ListOfPolicieArns: [
        "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
        "arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy",
        podExecutionPolicy.policy.arn.apply(arn => arn),
    ],
    tags: tags,
}, {
    dependsOn: podExecutionPolicy
});

export const saRoleArn = saRole.role.arn;
