#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.storage_stack import StorageStack
from stacks.iam_stack import IamStack
from stacks.lambda_stack import LambdaStack
from stacks.monitoring_stack import MonitoringStack
from stacks.oidc_stack import OidcStack


app = cdk.App()

region = app.node.try_get_context("region") or "eu-west-2"
env = cdk.Environment(account=cdk.Aws.ACCOUNT_ID, region=region)

vpc_stack = VpcStack(app, "WslMlopsVpcStack", env=env)
storage_stack = StorageStack(app, "WslMlopsStorageStack", env=env)

iam_stack = IamStack(
    app,
    "WslMlopsIamStack",
    raw_bucket=storage_stack.raw_bucket,
    pred_bucket=storage_stack.pred_bucket,
    kms_key=storage_stack.kms_key,
    env=env,
)

lambda_stack = LambdaStack(
    app,
    "WslMlopsLambdaStack",
    vpc=vpc_stack.vpc,
    vpc_subnet_ids=vpc_stack.private_subnet_ids,
    endpoint_security_group_id=vpc_stack.endpoint_security_group_id,
    raw_bucket=storage_stack.raw_bucket,
    pred_bucket=storage_stack.pred_bucket,
    sagemaker_role_arn=iam_stack.sagemaker_role.role_arn,
    lambda_role=iam_stack.lambda_role,
    env=env,
)

monitoring_stack = MonitoringStack(
    app,
    "WslMlopsMonitoringStack",
    deploy_lambda=lambda_stack.deploy_lambda,
    predict_lambda=lambda_stack.predict_lambda,
    env=env,
)

oidc_stack = OidcStack(app, "WslMlopsOidcStack", env=env)

storage_stack.add_dependency(vpc_stack)
iam_stack.add_dependency(storage_stack)
lambda_stack.add_dependency(iam_stack)
monitoring_stack.add_dependency(lambda_stack)

cdk.Tags.of(app).add("Project", "WSLAnalytics")
cdk.Tags.of(app).add("Component", "MLOps")

app.synth()
