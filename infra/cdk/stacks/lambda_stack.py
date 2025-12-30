from aws_cdk import Stack, Duration, aws_lambda as _lambda, aws_ec2 as ec2, aws_s3 as s3, aws_ssm as ssm
from constructs import Construct

class LambdaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        vpc_subnet_ids: list[str],
        endpoint_security_group_id: str,
        raw_bucket: s3.Bucket,
        pred_bucket: s3.Bucket,
        sagemaker_role_arn: str,
        lambda_role,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        subnet_selection = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
        sg = ec2.SecurityGroup(self, "LambdaSg", vpc=vpc, allow_all_outbound=True)
        sg.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(443), "HTTPS from VPC")

        common_env = {
            "RAW_BUCKET": raw_bucket.bucket_name,
            "PRED_BUCKET": pred_bucket.bucket_name,
            "SAGEMAKER_ROLE_ARN": sagemaker_role_arn,
            "VPC_SUBNET_IDS": ",".join(vpc_subnet_ids),
            "ENDPOINT_SECURITY_GROUP_ID": endpoint_security_group_id,
            "ENDPOINT_LIFECYCLE": "ephemeral",
        }

        self.deploy_lambda = _lambda.Function(
            self,
            "DeployEndpointLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="deploy_endpoint.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            memory_size=512,
            role=lambda_role,
            vpc=vpc,
            vpc_subnets=subnet_selection,
            security_groups=[sg],
            environment=common_env,
        )

        self.predict_lambda = _lambda.Function(
            self,
            "PredictWeeklyLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="predict_weekly.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            memory_size=512,
            role=lambda_role,
            vpc=vpc,
            vpc_subnets=subnet_selection,
            security_groups=[sg],
            environment=common_env,
        )

        ssm.StringParameter(
            self,
            "DeployLambdaArnParam",
            parameter_name="/wsl-mlops/deploy_lambda_arn",
            string_value=self.deploy_lambda.function_arn,
        )
        ssm.StringParameter(
            self,
            "PredictLambdaArnParam",
            parameter_name="/wsl-mlops/predict_lambda_arn",
            string_value=self.predict_lambda.function_arn,
        )
