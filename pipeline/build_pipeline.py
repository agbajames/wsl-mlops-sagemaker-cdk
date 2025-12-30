import argparse
import boto3
import sagemaker
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.sklearn.estimator import SKLearn
from sagemaker.sklearn.model import SKLearnModel
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.workflow.model_step import ModelStep
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.workflow.lambda_step import LambdaStep, LambdaOutput, LambdaOutputTypeEnum, Lambda

SSM = boto3.client("ssm")

def ssm_get(name: str) -> str:
    return SSM.get_parameter(Name=name)["Parameter"]["Value"]

def build() -> Pipeline:
    raw_bucket_uri = ssm_get("/wsl-mlops/raw_bucket_uri")
    pred_bucket_uri = ssm_get("/wsl-mlops/pred_bucket_uri")
    role_arn = ssm_get("/wsl-mlops/sagemaker_role_arn")
    deploy_lambda_arn = ssm_get("/wsl-mlops/deploy_lambda_arn")
    predict_lambda_arn = ssm_get("/wsl-mlops/predict_lambda_arn")

    boto_sess = boto3.Session()
    sm_sess = sagemaker.session.Session(boto_session=boto_sess)
    region = boto_sess.region_name

    raw_data_s3_uri = ParameterString("RawDataS3Uri", default_value=f"{raw_bucket_uri}/raw/wsldata.csv")
    fixtures_s3_uri = ParameterString("FixturesS3Uri", default_value=f"{raw_bucket_uri}/fixtures/upcoming_fixtures.csv")
    gameweek = ParameterString("Gameweek", default_value="GW01")

    # 1) Preprocess (Processing)
    proc = SKLearnProcessor(framework_version="1.2-1", role=role_arn, instance_type="ml.t3.medium", instance_count=1, sagemaker_session=sm_sess)
    preprocess = ProcessingStep(
        name="Preprocess",
        processor=proc,
        code="pipeline/steps/preprocess.py",
        inputs=[ProcessingInput(source=raw_data_s3_uri, destination="/opt/ml/processing/input")],
        outputs=[
            ProcessingOutput(output_name="train", source="/opt/ml/processing/train", destination=f"{raw_bucket_uri}/processed/train"),
            ProcessingOutput(output_name="val", source="/opt/ml/processing/val", destination=f"{raw_bucket_uri}/processed/val"),
            ProcessingOutput(output_name="test", source="/opt/ml/processing/test", destination=f"{raw_bucket_uri}/processed/test"),
        ],
    )

    # 2) Train (Training)
    est = SKLearn(
        entry_point="train.py",
        source_dir="pipeline/steps",
        framework_version="1.2-1",
        role=role_arn,
        instance_type="ml.t3.medium",
        instance_count=1,
        output_path=f"{raw_bucket_uri}/models",
        sagemaker_session=sm_sess,
    )
    train = TrainingStep(
        name="Train",
        estimator=est,
        inputs={
            "train": sagemaker.inputs.TrainingInput(s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri),
            "val": sagemaker.inputs.TrainingInput(s3_data=preprocess.properties.ProcessingOutputConfig.Outputs["val"].S3Output.S3Uri),
        },
    )

    # 3) Evaluate (Processing)
    eval_proc = SKLearnProcessor(framework_version="1.2-1", role=role_arn, instance_type="ml.t3.medium", instance_count=1, sagemaker_session=sm_sess)
    evaluate = ProcessingStep(
        name="Evaluate",
        processor=eval_proc,
        code="pipeline/steps/evaluate.py",
        inputs=[
            ProcessingInput(source=train.properties.ModelArtifacts.S3ModelArtifacts, destination="/opt/ml/processing/model"),
            ProcessingInput(source=preprocess.properties.ProcessingOutputConfig.Outputs["test"].S3Output.S3Uri, destination="/opt/ml/processing/test"),
        ],
        outputs=[
            ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation", destination=f"{raw_bucket_uri}/evaluation")
        ],
    )

    # 4) Register Model (Model Registry)
    metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri=f"{evaluate.properties.ProcessingOutputConfig.Outputs['evaluation'].S3Output.S3Uri}/evaluation.json",
            content_type="application/json",
        )
    )

    sklearn_model = SKLearnModel(
        model_data=train.properties.ModelArtifacts.S3ModelArtifacts,
        role=role_arn,
        entry_point="inference.py",
        source_dir="pipeline/steps",
        framework_version="1.2-1",
        py_version="py3",
        sagemaker_session=sm_sess,
    )

    register_step = ModelStep(
        name="RegisterModel",
        step_args=sklearn_model.register(
            content_types=["application/json"],
            response_types=["application/json"],
            inference_instances=["ml.t3.medium"],
            transform_instances=["ml.t3.medium"],
            model_package_group_name="wsl-elo-models",
            approval_status="Approved",
            model_metrics=metrics,
        ),
    )

    # 5) Deploy endpoint (LambdaStep)
    deploy_lambda = Lambda(function_arn=deploy_lambda_arn)
    deploy = LambdaStep(
        name="DeployEndpoint",
        lambda_func=deploy_lambda,
        inputs={
            "model_package_arn": register_step.properties.ModelPackageArn,
            "endpoint_name": "wsl-elo-endpoint",
            "instance_type": "ml.t3.medium",
        },
        outputs=[
            LambdaOutput(
                output_name="endpoint_name",
                output_type=LambdaOutputTypeEnum.String,
                path="$.endpoint_name",
            )
        ],
    )

    # 6) Predict (LambdaStep)
    predict_lambda = Lambda(function_arn=predict_lambda_arn)
    _ = LambdaStep(
        name="PredictWeekly",
        lambda_func=predict_lambda,
        inputs={
            "endpoint_name": deploy.outputs["endpoint_name"],
            "fixtures_s3_uri": fixtures_s3_uri,
            "gameweek": gameweek,
            "lifecycle": "ephemeral",
            "output_prefix": f"{pred_bucket_uri}/predictions",
        },
    )

    pipeline = Pipeline(
        name="wsl-mlops-pipeline",
        parameters=[raw_data_s3_uri, fixtures_s3_uri, gameweek],
        steps=[preprocess, train, evaluate, register_step, deploy, _],
        sagemaker_session=sm_sess,
    )

    # Persist pipeline name
    SSM.put_parameter(Name="/wsl-mlops/pipeline_name", Value=pipeline.name, Type="String", Overwrite=True)
    return pipeline

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upsert", action="store_true")
    args = ap.parse_args()

    if not args.upsert:
        raise SystemExit("Use --upsert to create/update the pipeline.")

    role_arn = ssm_get("/wsl-mlops/sagemaker_role_arn")
    p = build()
    p.upsert(role_arn=role_arn)
    print(f"Upserted pipeline: {p.name}")

if __name__ == "__main__":
    main()
