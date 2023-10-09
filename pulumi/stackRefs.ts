import * as pulumi from '@pulumi/pulumi'
import { accountId, region, project, stack } from "./globals";

const config = new pulumi.Config(project);
const org = config.require("org");
const stackRef = new pulumi.StackReference(`${org}/${project}-infra/${stack}`)

export const securityGroupId = stackRef.getOutput("securityGroupId");
export const DocumentsArn = stackRef.getOutput("DocumentsArn");
export const EnvelopeCallbacksArn = stackRef.getOutput("EnvelopeCallbacksArn");
export const EnvelopesArn = stackRef.getOutput("EnvelopesArn");
export const bucketArn = stackRef.getOutput("bucketArn");
export const templatesBucketArn = stackRef.getOutput("templatesBucketArn");
export const certArnWebHook = stackRef.getOutput("certArnWebHook");
