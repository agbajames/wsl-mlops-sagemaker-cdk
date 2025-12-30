from aws_cdk import Stack, Fn, aws_ec2 as ec2, aws_ssm as ssm
from constructs import Construct

class VpcStack(Stack):
    """
    VPC for hosting SageMaker endpoint + VPC-attached Lambdas.

    This stack is NAT-free (nat_gateways=0) and uses VPC endpoints.
    Note: For SageMaker hosting in private subnets, you typically need:
      - S3 gateway endpoint (free)
      - Interface endpoints for logs + ECR (+ optionally STS) to avoid NAT.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "WslMlopsVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PrivateIsolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                )
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # SG used by interface endpoints + SageMaker models/endpoints
        endpoint_sg = ec2.SecurityGroup(
            self,
            "EndpointSecurityGroup",
            vpc=self.vpc,
            description="Security group for VPC endpoints and SageMaker endpoint",
            allow_all_outbound=True,
        )
        endpoint_sg.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(443),
            "Allow HTTPS from within VPC",
        )

        # S3 gateway endpoint (free)
        self.vpc.add_gateway_endpoint(
            "S3GatewayEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # Interface endpoints (PrivateLink)
        interface_services = [
            ec2.InterfaceVpcEndpointAwsService.ECR,
            ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_API,
            ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME,
            ec2.InterfaceVpcEndpointAwsService.STS,
        ]

        for svc in interface_services:
            self.vpc.add_interface_endpoint(
                f"{svc.short_name.replace('.', '').title()}Endpoint",
                service=svc,
                private_dns_enabled=True,
                security_groups=[endpoint_sg],
                subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            )
        
        isolated_subnet_ids = self.vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        ).subnet_ids
        self.private_subnet_ids = isolated_subnet_ids

        self.endpoint_security_group_id = endpoint_sg.security_group_id

        # Persist VPC config to SSM for Lambda + tooling
        ssm.StringParameter(
            self,
            "SubnetIdsParam",
            parameter_name="/wsl-mlops/vpc_private_subnet_ids",
            string_value=Fn.join(",", self.private_subnet_ids),
        )
        ssm.StringParameter(
            self,
            "EndpointSgParam",
            parameter_name="/wsl-mlops/endpoint_sg_id",
            string_value=self.endpoint_security_group_id,
        )