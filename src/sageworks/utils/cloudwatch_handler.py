import os
import sys
import logging
from botocore.exceptions import ClientError
from datetime import datetime
import getpass
import watchtower

# SageWorks imports
from sageworks.aws_service_broker.aws_account_clamp import AWSAccountClamp
from sageworks.utils.docker_utils import running_on_docker


class CloudWatchHandler:
    """A CloudWatch Logs handler for SageWorks"""

    def __init__(self, logger):
        self.logger = logger
        self.account_clamp = AWSAccountClamp()
        self.boto3_session = self.account_clamp.get_boto3_session()
        self.log_stream_name = self.determine_log_stream()

    def add_cloudwatch_logs_handler(self):
        """Add a CloudWatch Logs handler to the logger"""
        try:
            cloudwatch_client = self.boto3_session.client("logs")
            self.logger.info("Adding CloudWatch Logs Handler...")
            self.logger.info(f"Log Stream Name: {self.log_stream_name}")

            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                log_group="SageWorksLogGroup",
                stream_name=self.log_stream_name,
                boto3_client=cloudwatch_client,
            )

            # Create a formatter for CloudWatch without the timestamp
            cloudwatch_formatter = logging.Formatter("(%(filename)s:%(lineno)d) %(levelname)s %(message)s")
            cloudwatch_handler.setFormatter(cloudwatch_formatter)

            # Add the CloudWatch handler to the logger
            self.logger.addHandler(cloudwatch_handler)
        except ClientError as e:
            self.logger.error(f"Failed to set up CloudWatch Logs handler: {e}")

    @staticmethod
    def get_executable_name(argv):
        try:
            script_path = argv[0]
            base_name = os.path.basename(script_path)
            return os.path.splitext(base_name)[0]
        except Exception:
            return None

    def determine_log_stream(self):
        """Determine the log stream name based on the environment."""
        executable_name = self.get_executable_name(sys.argv)
        unique_id = self.get_unique_identifier()

        if self.running_on_lambda():
            job_name = executable_name or os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "unknown")
            return f"lambda/{job_name}/{unique_id}"
        elif self.running_on_glue():
            job_name = executable_name or os.environ.get("GLUE_JOB_NAME", "unknown")
            return f"glue/{job_name}/{unique_id}"
        elif running_on_docker():
            job_name = executable_name or os.environ.get("SERVICE_NAME", "unknown")
            return f"docker/{job_name}/{unique_id}"
        else:
            return f"laptop/{getpass.getuser()}/{unique_id}"

    @staticmethod
    def get_unique_identifier():
        """Get a unique identifier for the log stream."""
        job_id = CloudWatchHandler.get_job_id_from_environment()
        return job_id or datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")

    @staticmethod
    def get_job_id_from_environment():
        """Try to retrieve the job ID from Glue or Lambda environment variables."""
        return os.environ.get("GLUE_JOB_ID") or os.environ.get("AWS_LAMBDA_REQUEST_ID")

    @staticmethod
    def running_on_lambda():
        """Check if running in AWS Lambda."""
        return 'AWS_LAMBDA_FUNCTION_NAME' in os.environ

    @staticmethod
    def running_on_glue():
        """Check if running in AWS Glue."""
        return 'GLUE_JOB_NAME' in os.environ


if __name__ == "__main__":
    # Example usage
    logger = logging.getLogger('SageWorks')
    logger.setLevel(logging.INFO)
    cloud_watch_handler = CloudWatchHandler(logger)
    cloud_watch_handler.add_cloudwatch_logs_handler()
