"""This Script creates an empty model group, a model group without any models

Models:
    - empty-model-group
"""

import logging
from botocore.exceptions import ClientError
from sageworks.aws_service_broker.aws_account_clamp import AWSAccountClamp
from sageworks.api.meta import Meta

# Setup the logger
log = logging.getLogger("sageworks")


# Helper method to create an 'empty' model group
def create_model_package_group(group_name, boto3_session):
    sm_client = boto3_session.client("sagemaker")

    try:
        response = sm_client.create_model_package_group(
            ModelPackageGroupName=group_name,
            ModelPackageGroupDescription="Your description here",  # Add a relevant description
        )
        log.info(f"Model Package Group '{group_name}' created successfully.")
        return response
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException" and "already exists" in e.response["Error"]["Message"]:
            log.info(f"Model Package Group '{group_name}' already exists.")
            return None
        else:
            # Re-raise any other exceptions
            raise


if __name__ == "__main__":
    # This forces a refresh on the metadata we get from AWS
    Meta().models(refresh=True)

    # Create an empty Model Package Group
    boto3_session = AWSAccountClamp().boto3_session
    create_model_package_group("empty-model-group", boto3_session)
