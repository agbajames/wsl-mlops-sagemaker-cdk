# WSLAnalytics — MLOps (CDK + SageMaker Pipelines)

This repo builds a production-grade weekly prediction workflow:

- Train an Elo-based model weekly (SageMaker Pipelines)
- Register in SageMaker Model Registry
- Deploy/update a **VPC** SageMaker real-time endpoint
- Generate W/D/L probabilities for upcoming fixtures
- Write a CSV to S3 (`predictions/<gameweek>/wsl_predictions.csv`)
- Optional: **ephemeral** endpoint lifecycle (delete endpoint after generating predictions)

## Quickstart (local)

```bash
make venv
source .venv/bin/activate
make install-all
make test
```

## Deploy to AWS (first time)

```bash
make cdk-bootstrap
make cdk-deploy
make upload-seed
make upsert-pipeline
```

Run a pipeline execution:

```bash
RAW_URI="$(python scripts/print_outputs.py --key RAW_BUCKET_URI)"
python scripts/start_pipeline.py   --raw-s3-uri "${RAW_URI}/raw/wsldata.csv"   --fixtures-s3-uri "${RAW_URI}/fixtures/upcoming_fixtures.csv"   --gameweek "GW01"
```

## Important notes

- The **CDK** deploy stores outputs in **SSM Parameter Store** (`/wsl-mlops/*`).
- The SageMaker endpoint is deployed **in the VPC**. If you set `ENDPOINT_LIFECYCLE=ephemeral`,
  the prediction Lambda deletes the endpoint after writing the CSV.
- Pricing varies by region. Validate with AWS Pricing Calculator and your usage profile.
