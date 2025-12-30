from aws_cdk import Stack, aws_iam as iam, aws_s3 as s3, aws_kms as kms, aws_ssm as ssm
from constructs import Construct

class IamStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        raw_bucket: s3.Bucket,
        pred_bucket: s3.Bucket,
        kms_key: kms.Key,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.sagemaker_role = iam.Role(
            self,
            "SageMakerExecRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
            ],
        )
        raw_bucket.grant_read_write(self.sagemaker_role)
        pred_bucket.grant_read_write(self.sagemaker_role)
        kms_key.grant_encrypt_decrypt(self.sagemaker_role)

        # Lambda execution role
        self.lambda_role = iam.Role(
            self,
            "LambdaExecRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
            ],
        )
        raw_bucket.grant_read(self.lambda_role)
        pred_bucket.grant_read_write(self.lambda_role)
        kms_key.grant_encrypt_decrypt(self.lambda_role)

        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateModel",
                    "sagemaker:DeleteModel",
                    "sagemaker:CreateEndpointConfig",
                    "sagemaker:DeleteEndpointConfig",
                    "sagemaker:CreateEndpoint",
                    "sagemaker:UpdateEndpoint",
                    "sagemaker:DeleteEndpoint",
                    "sagemaker:DescribeEndpoint",
                    "sagemaker:DescribeEndpointConfig",
                    "sagemaker:InvokeEndpoint",
                    "sagemaker:DescribeModelPackage",
                ],
                resources=["*"],
            )
        )
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[self.sagemaker_role.role_arn],
            )
        )
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter","ssm:GetParameters"],
                resources=["*"],
            )
        )

        ssm.StringParameter(
            self,
            "SageMakerRoleArnParam",
            parameter_name="/wsl-mlops/sagemaker_role_arn",
            string_value=self.sagemaker_role.role_arn,
        )
