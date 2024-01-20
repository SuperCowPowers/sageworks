from aws_cdk import (
    Environment,
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct
from typing import Any, List
from dataclasses import dataclass, field


@dataclass
class SageworksCoreStackProps:
    sageworks_bucket: str
    sageworks_role_name: str
    sso_group: str
    additional_buckets: List[str] = field(default_factory=list)


class SageworksCoreStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env: Environment,
        props: SageworksCoreStackProps,
        **kwargs: Any,
    ) -> None:
        desc = "SageWorks Core Stack: SageWorks-ExecutionRole (API) and  AWSGlueServiceRole-SageWorks (Glue)"
        super().__init__(scope, construct_id, description=desc, **kwargs)

        # Grab our properties
        self.account_id = env.account
        self.sageworks_bucket = props.sageworks_bucket
        self.sageworks_role_name = props.sageworks_role_name
        self.sso_group = props.sso_group
        self.additional_buckets = props.additional_buckets

        # Get the SageWorks Artifact Bucket (must be created before running this script)
        self.artifact_bucket = self.get_artifact_bucket(self.sageworks_bucket)

        # Create our main SageWorks Execution Role
        self.sageworks_api_execution_role = self.create_api_execution_role()

    def get_artifact_bucket(self, bucket_name: str) -> s3.IBucket:
        # Reference an existing bucket by name
        return s3.Bucket.from_bucket_name(self, id="ExistingArtifactBucket", bucket_name=bucket_name)

    def create_api_execution_role(self) -> iam.Role:
        """Create the SageWorks Execution Role for API-related tasks"""

        # Define the base assumed by principals with ECS service principal
        assumed_by = iam.CompositePrincipal(
            iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            iam.ServicePrincipal("sagemaker.amazonaws.com"),
            iam.ServicePrincipal("glue.amazonaws.com"),
        )

        # If sso_group is provided, add the condition to the trust relationship
        if self.sso_group:
            sso_group_arn_1 = (
                f"arn:aws:iam::{self.account_id}:role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_{self.sso_group}_*"
            )
            sso_group_arn_2 = f"arn:aws:iam::{self.account_id}:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_{self.sso_group}_*"
            condition = {"ArnLike": {"aws:PrincipalArn": [sso_group_arn_1, sso_group_arn_2]}}
            assumed_by.add_principals(iam.AccountPrincipal(self.account_id).with_conditions(condition))
        else:
            assumed_by.add_principals(iam.AccountPrincipal(self.account_id))

        # Create the role with the trust relationship and managed policies
        api_execution_role = iam.Role(
            self,
            id=self.sageworks_role_name,
            assumed_by=assumed_by,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
            role_name=self.sageworks_role_name,
        )
        # Policy statement for main Sageworks Bucket and Athena Results
        api_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:*", "s3-object-lambda:*"],
                resources=[
                    "arn:aws:s3:::aws-athena-query-results*/*",
                    f"arn:aws:s3:::{self.sageworks_bucket}/*",
                ],
            )
        )

        # ECS DescribeServices
        api_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecs:DescribeServices"],
                resources=["*"],
            )
        )

        # ELB DescribeLoadBalancers
        api_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["elasticloadbalancing:DescribeLoadBalancers"],
                resources=["*"],
            )
        )

        # Getting Athena Workgroup
        api_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["athena:GetWorkGroup"],
                resources=["*"],
            )
        )

        # Add permissions for additional buckets
        for bucket in self.additional_buckets:
            api_execution_role.add_to_policy(
                iam.PolicyStatement(actions=["s3:*"], resources=[f"arn:aws:s3:::{bucket}/*"])
            )

        return api_execution_role
