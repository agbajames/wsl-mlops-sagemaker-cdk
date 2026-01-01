from aws_cdk import Stack, aws_iam as iam
from constructs import Construct

class OidcStack(Stack):
    """
    GitHub Actions OIDC role.

    For demo simplicity this attaches AdministratorAccess. For production,
    scope this down (CloudFormation + specific service actions).
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        provider = iam.OpenIdConnectProvider(
            self,
            "GitHubProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        # Github repo:
        repo_subject = "repo:agbajames/wsl-mlops-sagemaker-cdk:ref:refs/heads/main"

        self.role = iam.Role(
            self,
            "GitHubActionsRole",
            assumed_by=iam.FederatedPrincipal(
                federated=provider.open_id_connect_provider_arn,
                conditions={
                    "StringLike": {"token.actions.githubusercontent.com:sub": repo_subject},
                    "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
            ],
        )
