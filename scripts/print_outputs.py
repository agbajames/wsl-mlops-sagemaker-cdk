import argparse
import sys
import boto3

PARAMS = {
    "RAW_BUCKET_URI": "/wsl-mlops/raw_bucket_uri",
    "PRED_BUCKET_URI": "/wsl-mlops/pred_bucket_uri",
    "PIPELINE_NAME": "/wsl-mlops/pipeline_name",
    "DEPLOY_LAMBDA_ARN": "/wsl-mlops/deploy_lambda_arn",
    "PREDICT_LAMBDA_ARN": "/wsl-mlops/predict_lambda_arn",
    "SAGEMAKER_ROLE_ARN": "/wsl-mlops/sagemaker_role_arn",
}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, choices=PARAMS.keys())
    args = ap.parse_args()

    ssm = boto3.client("ssm")
    try:
        print(ssm.get_parameter(Name=PARAMS[args.key])["Parameter"]["Value"])
    except ssm.exceptions.ParameterNotFound:
        print(f"Parameter not found: {PARAMS[args.key]}", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
