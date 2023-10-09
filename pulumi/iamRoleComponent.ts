import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const stackName = pulumi.getStack();
const projectName = pulumi.getProject();

export class IamRole extends pulumi.ComponentResource {
    public role: aws.iam.Role;
    public tags: object = {
        environment: stackName,
        app: projectName
    }

    constructor(
        name: string,
        args: {
            // assumeRolePrincipal?: string[],
            assumeRolePolicy: any,
            ListOfPolicieArns?: any,
            tags?: any,
        },
        opts?: pulumi.ComponentResourceOptions) {
        super("pkg:iam:iamRole", name, args, opts);

        // Creates a role and attches the EKS worker node IAM managed policies
        this.role = new aws.iam.Role(
            name,
            {
                assumeRolePolicy: args.assumeRolePolicy,
                tags: args.tags || this.tags,
            },
            { parent: this }
        );

        let counter = 0;
        const listOfPolicies = args.ListOfPolicieArns || undefined

        if (listOfPolicies) {
            for (const policy of listOfPolicies) {
                // Create RolePolicyAttachment without returning it.
                const rpa = new aws.iam.RolePolicyAttachment(
                    `${name}-policy-${counter++}`,
                    { policyArn: policy, role: this.role },
                    { parent: this }
                );
            }
        }

        this.registerOutputs({
            role: this.role.arn,
        });
    }
}
