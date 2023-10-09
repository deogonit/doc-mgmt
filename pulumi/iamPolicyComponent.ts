import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const stackName = pulumi.getStack();
const projectName = pulumi.getProject();


export class IamPolicy extends pulumi.ComponentResource {
    public policy: aws.iam.Policy;
    public path: string = "/";
    public description: string = `Description ${projectName}-${stackName}`;
    public tags: object = {
        environment: stackName,
        app: projectName
    }

    constructor(
        name: string,
        args: {
            path?: string,
            description?: string,
            listOfStatements: any,
            tags?: any,
        },
        opts?: pulumi.ComponentResourceOptions) {
        super("pkg:iam:iamPolicy", name, args, opts);

        this.policy = new aws.iam.Policy(
            name,
            {
                path: args.path || this.path,
                description: args.description || this.description,
                policy: args.listOfStatements,
                tags: args.tags || this.tags,
            },
            { parent: this }
        );


        this.registerOutputs({
            arn: this.policy.arn,
        });
    }
}
