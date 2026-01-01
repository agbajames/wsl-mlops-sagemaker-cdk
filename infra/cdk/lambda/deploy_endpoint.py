import json
import os
from datetime import datetime
from typing import Any, Dict, List

import boto3

sm = boto3.client("sagemaker")

def _split_csv_env(name: str) -> List[str]:
    val = os.environ.get(name, "")
    parts = [p.strip() for p in val.split(",") if p.strip()]
    if not parts:
        raise ValueError(f"Missing/empty env var: {name}")
    return parts

def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Deploy/update SageMaker endpoint from a Model Package.

    Expected event:
      - model_package_arn (required)
      - endpoint_name (optional, default 'wsl-elo-endpoint')
      - instance_type (optional, default 'ml.t3.medium')
    """
    model_package_arn = event["model_package_arn"]
    endpoint_name = event.get("endpoint_name", "wsl-elo-endpoint")
    instance_type = event.get("instance_type", "ml.m5.large")

    role_arn = os.environ["SAGEMAKER_ROLE_ARN"]
    subnet_ids = _split_csv_env("VPC_SUBNET_IDS")
    sg_ids = [os.environ["ENDPOINT_SECURITY_GROUP_ID"]]

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_name = f"{endpoint_name}-model-{ts}"
    cfg_name = f"{endpoint_name}-cfg-{ts}"

    sm.create_model(
        ModelName=model_name,
        ExecutionRoleArn=role_arn,
        Containers=[{"ModelPackageName": model_package_arn}],
        VpcConfig={"Subnets": subnet_ids, "SecurityGroupIds": sg_ids},
    )

    sm.create_endpoint_config(
        EndpointConfigName=cfg_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": model_name,
                "InitialInstanceCount": 1,
                "InstanceType": instance_type,
                "InitialVariantWeight": 1.0,
            }
        ],
    )

    try:
        sm.describe_endpoint(EndpointName=endpoint_name)
        sm.update_endpoint(EndpointName=endpoint_name, EndpointConfigName=cfg_name)
    except sm.exceptions.ClientError as e:
        if "Could not find endpoint" in str(e) or "ValidationException" in str(e):
            sm.create_endpoint(EndpointName=endpoint_name, EndpointConfigName=cfg_name)
        else:
            raise

    waiter = sm.get_waiter("endpoint_in_service")
    waiter.wait(EndpointName=endpoint_name, WaiterConfig={"Delay": 30, "MaxAttempts": 40})

    return {
        "endpoint_name": endpoint_name,
        "model_name": model_name,
        "endpoint_config_name": cfg_name,
        "model_package_arn": model_package_arn,
    }
