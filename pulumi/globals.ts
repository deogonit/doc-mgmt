import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const config = new pulumi.Config('aws');
const current = aws.getCallerIdentity({});

export const project = pulumi.getProject();
export const stack = pulumi.getStack();

export const accountId = current.then(current => current.accountId);
export const region = config.require('region')
