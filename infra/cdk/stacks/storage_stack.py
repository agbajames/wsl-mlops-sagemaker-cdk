from aws_cdk import Stack, RemovalPolicy, aws_kms as kms, aws_s3 as s3, aws_ssm as ssm
from constructs import Construct

class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.kms_key = kms.Key(
            self,
            "WslMlopsKey",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,
            description="KMS key for WSLAnalytics buckets (dev: DESTROY).",
        )

        self.raw_bucket = s3.Bucket(
            self,
            "RawBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.pred_bucket = s3.Bucket(
            self,
            "PredBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        ssm.StringParameter(
            self,
            "RawBucketUri",
            parameter_name="/wsl-mlops/raw_bucket_uri",
            string_value=f"s3://{self.raw_bucket.bucket_name}",
        )
        ssm.StringParameter(
            self,
            "PredBucketUri",
            parameter_name="/wsl-mlops/pred_bucket_uri",
            string_value=f"s3://{self.pred_bucket.bucket_name}",
        )
