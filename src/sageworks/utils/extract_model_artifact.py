"""ExtractModelArtifact is a utility class that reanimates a model joblib file."""
import tarfile
import tempfile
import joblib
import awswrangler as wr
import os
import glob
import xgboost  # noqa: F401

# SageWorks Imports
from sageworks.aws_service_broker.aws_account_clamp import AWSAccountClamp


class ExtractModelArtifact:
    def __init__(self, endpoint_name):
        """ExtractModelArtifact Class
        Args:
            endpoint_name (str): Name of the endpoint to extract the model artifact from
        """
        self.endpoint_name = endpoint_name

        # Initialize SageMaker client
        self.sagemaker_client = AWSAccountClamp().sagemaker_client()

    def get_model_artifact(self):
        """Get the model artifact from the endpoint"""
        model_artifact_uri = self.get_model_data_uri()
        return self.download_and_extract_model(model_artifact_uri)

    def get_model_data_uri(self) -> str:
        """Get the model artifact URI (S3 Path) from the endpoint
        Returns:
            str: URI (S3 Path) to the model artifact
        """

        # Get the endpoint configuration
        endpoint_desc = self.sagemaker_client.describe_endpoint(EndpointName=self.endpoint_name)
        endpoint_config_desc = self.sagemaker_client.describe_endpoint_config(
            EndpointConfigName=endpoint_desc["EndpointConfigName"]
        )

        # Extract the model name from the endpoint configuration
        # Assuming single model for simplicity; adjust if handling multiple models
        model_name = endpoint_config_desc["ProductionVariants"][0]["ModelName"]

        # Get the model description using the Model ARN
        model_desc = self.sagemaker_client.describe_model(ModelName=model_name)

        # Check if 'Containers' (real-time) or 'PrimaryContainer' (serverless) is used
        if "Containers" in model_desc:
            # Real-time model
            model_package_arn = model_desc["Containers"][0].get("ModelPackageName")
        elif "PrimaryContainer" in model_desc:
            # Serverless model
            model_package_arn = model_desc["PrimaryContainer"].get("ModelPackageName")

        # Throw an error if the model package ARN is not found
        if model_package_arn is None:
            raise ValueError("ModelPackageName not found in the model description")

        # Now get the model package description and from that the model artifact URI
        model_package_desc = self.sagemaker_client.describe_model_package(ModelPackageName=model_package_arn)
        inference_spec = model_package_desc.get("InferenceSpecification", {})
        containers = inference_spec.get("Containers", [])
        if containers:
            model_data_url = containers[0].get("ModelDataUrl")
            return model_data_url
        else:
            raise ValueError("ModelDataUrl not found in the model package description")

    @staticmethod
    def download_and_extract_model(model_artifact_uri):
        """Download and extract model artifact from S3, then load the model into memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            local_tar_path = os.path.join(tmpdir, "model.tar.gz")

            # Downloading the model artifact using awswrangler
            wr.s3.download(path=model_artifact_uri, local_file=local_tar_path)

            with tarfile.open(local_tar_path, "r:gz") as tar:
                tar.extractall(path=tmpdir)

            # Find the .joblib file in the extracted directory
            model_files = glob.glob(os.path.join(tmpdir, "*.joblib"))
            if not model_files:
                raise FileNotFoundError("No .joblib file found in the extracted model artifact.")
            model_file_path = model_files[0]

            # Load the model
            model = joblib.load(model_file_path)

        # Return the model after exiting the temporary directory context
        return model


if __name__ == "__main__":
    """Exercise the ExtractModelArtifact class"""

    # Create the Class and test it out
    my_endpoint = "abalone-regression-end"
    # my_endpoint = "hlm-phase2-class-0-230831-100-monitor"
    ema = ExtractModelArtifact(my_endpoint)

    # Test the lower level methods
    model_data_uri = ema.get_model_data_uri()
    print(f"Model Data URI: {model_data_uri}")
    my_model = ema.download_and_extract_model(model_data_uri)

    # Test the higher level method
    my_model = ema.get_model_artifact()
