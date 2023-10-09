import * as k8s from "@pulumi/kubernetes";
import { FileAsset } from "@pulumi/pulumi/asset";
import { env } from "node:process";
import { project, stack, accountId, region } from "./globals";
import { saRoleArn } from "./podExecutionRole";
import * as pulumi from "@pulumi/pulumi";
import { securityGroupId, certArnWebHook } from "./stackRefs";
import * as aws from "@pulumi/aws";

const config = new pulumi.Config(project);
const namespaceName = config.require("namespace");

const docuSignClientId = config.requireSecret("DOCU_SIGN__CLIENT_ID");
const docuSignPrivateKey = config.requireSecret("DOCU_SIGN__PRIVATE_KEY_ENCODED");
const docuSignAccountId = config.requireSecret("DOCU_SIGN__ACCOUNT_ID");
const docuSignUserId = config.requireSecret("DOCU_SIGN__IMPERSONATED_USER_ID");

const newRelicLicenseKey = config.requireSecret("NEW_RELIC_LICENSE_KEY");
const authApiKeys = config.requireSecret("AUTH__API_KEYS");

export const imageTag = env.IMAGE_TAG;

let internalAlbAnnotations = {
    "alb.ingress.kubernetes.io/scheme": "internal",
    "alb.ingress.kubernetes.io/healthcheck-path": "/health",
    "alb.ingress.kubernetes.io/target-type": "ip",
    "alb.ingress.kubernetes.io/group.name": "internal-apps",
    "alb.ingress.kubernetes.io/listen-ports": '[{"HTTP": 80}, {"HTTPS": 443}]',
    "alb.ingress.kubernetes.io/ssl-redirect": "443",
}

let publicAlbAnnotations = {
    "alb.ingress.kubernetes.io/scheme": "internet-facing",
    "alb.ingress.kubernetes.io/healthcheck-path": "/health",
    "alb.ingress.kubernetes.io/target-type": "ip",
    "alb.ingress.kubernetes.io/group.name": "public-apps",
    "alb.ingress.kubernetes.io/listen-ports": '[{"HTTP": 80}, {"HTTPS": 443}]',
    "alb.ingress.kubernetes.io/ssl-redirect": "443",
    "alb.ingress.kubernetes.io/manage-backend-security-group-rules": "true",
}

if (stack == "prod") {
    Object.assign(
        internalAlbAnnotations,
        { "alb.ingress.kubernetes.io/load-balancer-name": `${stack}-internal-apps` },
        { "alb.ingress.kubernetes.io/certificate-arn": certArnWebHook }
    );
    Object.assign(
        publicAlbAnnotations,
        { "alb.ingress.kubernetes.io/load-balancer-name": `${stack}-public-apps` },
        { "alb.ingress.kubernetes.io/certificate-arn": certArnWebHook },
        { "alb.ingress.kubernetes.io/security-groups": securityGroupId },
    );
} else {
    Object.assign(
        internalAlbAnnotations,
        { "alb.ingress.kubernetes.io/load-balancer-name": `vcluster-internal-apps` },
        { "external-dns.alpha.kubernetes.io/hostname": `${stack}-doc-mgmt.prime.coverwhale.dev.` },
    );
    Object.assign(
        publicAlbAnnotations,
        { "alb.ingress.kubernetes.io/load-balancer-name": `vcluster-public-apps` },
        { "external-dns.alpha.kubernetes.io/hostname": `${stack}-webhook-doc-mgmt.prime.coverwhale.dev.` },
    );
}

if (stack == "dev") {
    Object.assign(
        publicAlbAnnotations,
        { "alb.ingress.kubernetes.io/security-groups": securityGroupId },
    );
}

const release = new k8s.helm.v3.Release(`${project}`, {
    name: project,
    chart: "../k8s/helm",
    atomic: true,
    timeout: 900,
    createNamespace: true,
    namespace: namespaceName,

    valueYamlFiles: [new FileAsset(`../k8s/helm/${stack}-values.yaml`)],
    values: {
        namespace: namespaceName,
        deployment: {
            image: {
                registry: pulumi.interpolate`${accountId}.dkr.ecr.${region}.amazonaws.com`,
                name: `${project}-${stack}`,
                tag: imageTag,
            }
        },
        ingress: {
            annotations: internalAlbAnnotations,
        },
        ingress_public: {
            annotations: publicAlbAnnotations,
        },
        secrets: {
            internal: {
                data: {
                    DOCU_SIGN__CLIENT_ID: docuSignClientId,
                    DOCU_SIGN__PRIVATE_KEY_ENCODED: docuSignPrivateKey,
                    DOCU_SIGN__ACCOUNT_ID: docuSignAccountId,
                    DOCU_SIGN__IMPERSONATED_USER_ID: docuSignUserId,
                    NEW_RELIC_LICENSE_KEY: newRelicLicenseKey,
                    AUTH__API_KEYS: pulumi.interpolate`${authApiKeys}`
                }
            }
        },
        config_map: {
            data: {
                APP_VERSION: imageTag
            }
        },
        service_account: {
            role_arn: saRoleArn.apply(arn => arn)
        }
    }
})
let internalAlb: any;
internalAlb = stack == "prod" ? release.status.apply(status =>
    aws.lb.getLoadBalancerOutput({
        name: `${stack}-internal-apps`,
    })
) : undefined;

let publiclAlb: any;
publiclAlb = stack == "prod" ? release.status.apply(status =>
    aws.lb.getLoadBalancerOutput({
        name: `${stack}-public-apps`,
    })
) : undefined;

export const internalAlbDnsName = stack == "prod" ? internalAlb.dnsName : "";
export const publicAlbDnsName = stack == "prod" ? publiclAlb.dnsName : "";
export const albZoneId = stack == "prod" ? aws.lb.getHostedZoneIdOutput({ loadBalancerType: "application" }).id : "";

export const helm_id = release.id;
export const helm_status = release.status;
