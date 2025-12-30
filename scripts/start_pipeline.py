import argparse
from datetime import datetime
import boto3

def ssm_get(name: str) -> str:
    return boto3.client("ssm").get_parameter(Name=name)["Parameter"]["Value"]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-s3-uri", required=True)
    ap.add_argument("--fixtures-s3-uri", required=True)
    ap.add_argument("--gameweek", required=True)
    args = ap.parse_args()

    pipeline_name = ssm_get("/wsl-mlops/pipeline_name")
    sm = boto3.client("sagemaker")

    resp = sm.start_pipeline_execution(
        PipelineName=pipeline_name,
        PipelineParameters=[
            {"Name": "RawDataS3Uri", "Value": args.raw_s3_uri},
            {"Name": "FixturesS3Uri", "Value": args.fixtures_s3_uri},
            {"Name": "Gameweek", "Value": args.gameweek},
        ],
        PipelineExecutionDisplayName=f"{args.gameweek}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
    )
    print(resp["PipelineExecutionArn"])

if __name__ == "__main__":
    main()
