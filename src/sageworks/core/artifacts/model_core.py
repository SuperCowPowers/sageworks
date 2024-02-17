"""ModelCore: SageWorks ModelCore Class"""

import time
from datetime import datetime
import urllib.parse
from typing import Union
from enum import Enum
import botocore

import pandas as pd
import awswrangler as wr
from awswrangler.exceptions import NoFilesFound
from sagemaker import TrainingJobAnalytics
from sagemaker.model import Model as SagemakerModel

# SageWorks Imports
from sageworks.core.artifacts.artifact import Artifact
from sageworks.aws_service_broker.aws_service_broker import ServiceCategory
from sageworks.utils.aws_utils import newest_files, pull_s3_data


# Enumerated Model Types
class ModelType(Enum):
    """Enumerated Types for SageWorks Model Types"""

    CLASSIFIER = "classifier"
    REGRESSOR = "regressor"
    UNSUPERVISED = "unsupervised"
    TRANSFORMER = "transformer"
    UNKNOWN = "unknown"


class ModelCore(Artifact):
    """ModelCore: SageWorks ModelCore Class

    Common Usage:
        ```
        my_model = ModelCore(model_uuid)
        my_model.summary()
        my_model.details()
        ```
    """

    def __init__(self, model_uuid: str, force_refresh: bool = False, model_type: ModelType = None):
        """ModelCore Initialization
        Args:
            model_uuid (str): Name of Model in SageWorks.
            force_refresh (bool, optional): Force a refresh of the AWS Broker. Defaults to False.
            model_type (ModelType, optional): Set this for newly created Models. Defaults to None.
        """

        # Make sure the model_uuid is compliant
        model_uuid = self.compliant_uuid(model_uuid)

        # Call SuperClass Initialization
        super().__init__(model_uuid)

        # Grab an AWS Metadata Broker object and pull information for Models
        self.model_name = model_uuid
        aws_meta = self.aws_broker.get_metadata(ServiceCategory.MODELS, force_refresh=force_refresh)
        self.model_meta = aws_meta.get(self.model_name)
        if self.model_meta is None:
            self.log.important(f"Could not find model {self.model_name} within current visibility scope")
            self.latest_model = None
            self.model_type = ModelType.UNKNOWN
            return
        else:
            try:
                self.latest_model = self.model_meta[0]
                self.description = self.latest_model.get("ModelPackageDescription", "-")
                self.training_job_name = self._extract_training_job_name()
                if model_type:
                    self._set_model_type(model_type)
                else:
                    self.model_type = self._get_model_type()
            except (IndexError, KeyError):
                self.log.critical(f"Model {self.model_name} appears to be malformed. Delete and recreate it!")
                self.latest_model = None
                self.model_type = ModelType.UNKNOWN
                return

        # Set the Model Training S3 Path
        self.model_training_path = self.models_s3_path + "/training/" + self.model_name

        # Get our Endpoint Inference Path (might be None)
        self.endpoint_inference_path = self.get_endpoint_inference_path()

        # Call SuperClass Post Initialization
        super().__post_init__()

        # All done
        self.log.info(f"Model Initialized: {self.model_name}")

    def refresh_meta(self):
        """Refresh the Artifact's metadata"""
        self.model_meta = self.aws_broker.get_metadata(ServiceCategory.MODELS, force_refresh=True).get(self.model_name)
        self.latest_model = self.model_meta[0]
        self.description = self.latest_model.get("ModelPackageDescription", "-")
        self.training_job_name = self._extract_training_job_name()

    def compliant_uuid(self, uuid: str) -> str:
        """Make sure the uuid is compliant with Athena Table Name requirements

        Args:
            uuid (str): The uuid to make compliant

        Returns:
            str: The compliant uuid
        """
        return self.base_compliant_uuid(uuid, delimiter="-", just_warn=True)

    def exists(self) -> bool:
        """Does the model metadata exist in the AWS Metadata?"""
        if self.model_meta is None:
            self.log.debug(f"Model {self.model_name} not found in AWS Metadata!")
            return False
        return True

    def health_check(self) -> list[str]:
        """Perform a health check on this model
        Returns:
            list[str]: List of health issues
        """
        # Call the base class health check
        health_issues = super().health_check()

        # Model Type
        if self._get_model_type() == ModelType.UNKNOWN:
            health_issues.append("model_type_unknown")
        else:
            self.remove_health_tag("model_type_unknown")

        # Model Metrics
        if self.model_metrics() is None:
            health_issues.append("metrics_needed")
        else:
            self.remove_health_tag("metrics_needed")
        return health_issues

    def latest_model_object(self) -> SagemakerModel:
        """Return the latest AWS Sagemaker Model object for this SageWorks Model
        Returns:
           sagemaker.model.Model: AWS Sagemaker Model object
        """
        return SagemakerModel(
            model_data=self.model_package_arn(), sagemaker_session=self.sm_session, image_uri=self.model_image()
        )

    def model_metrics(self) -> Union[pd.DataFrame, None]:
        """Retrieve the training metrics for this model
        Returns:
            pd.DataFrame: DataFrame of the Model Metrics
        """
        # Grab the metrics from the SageWorks Metadata (try inference first, then training)
        metrics = self.sageworks_meta().get("sageworks_inference_metrics")
        if metrics is not None:
            return pd.DataFrame.from_dict(metrics)
        metrics = self.sageworks_meta().get("sageworks_training_metrics")
        return pd.DataFrame.from_dict(metrics) if metrics else None

    def confusion_matrix(self) -> Union[pd.DataFrame, None]:
        """Retrieve the confusion_matrix for this model
        Returns:
            pd.DataFrame: DataFrame of the Confusion Matrix (might be None)
        """
        # Grab the metrics from the SageWorks Metadata (try inference first, then training)
        cm = self.sageworks_meta().get("sageworks_inference_cm")
        if cm is not None:
            return cm
        cm = self.sageworks_meta().get("sageworks_training_cm")
        return pd.DataFrame.from_dict(cm) if cm else None

    def get_predictions(self) -> Union[pd.DataFrame, None]:
        """Retrieve the captured predictions for this model
        Returns:
            pd.DataFrame: DataFrame of the Captured Predictions (might be None)
        """

        # If an Endpoint, based on this model, has run inference, then grab those
        s3_path = f"{self.endpoint_inference_path}/inference_predictions.csv"
        df = pull_s3_data(s3_path)
        if df is not None:
            self.log.important(f"Grabbing Inference Predictions for {self.model_name}...")
            return df

        # Otherwise, grab the predictions from the training job
        else:
            self.log.important(f"Grabbing Validation Predictions for {self.model_name}...")
            s3_path = f"{self.model_training_path}/validation_predictions.csv"
            df = pull_s3_data(s3_path)
            return df

    def size(self) -> float:
        """Return the size of this data in MegaBytes"""
        return 0.0

    def aws_meta(self) -> dict:
        """Get ALL the AWS metadata for this artifact"""
        return self.latest_model

    def arn(self) -> str:
        """AWS ARN (Amazon Resource Name) for the Model Package Group"""
        return self.group_arn()

    def group_arn(self) -> str:
        """AWS ARN (Amazon Resource Name) for the Model Package Group"""
        return self.latest_model["ModelPackageGroupArn"]

    def model_package_arn(self) -> str:
        """AWS ARN (Amazon Resource Name) for the Model Package (within the Group)"""
        return self.latest_model["ModelPackageArn"]

    def model_container_info(self) -> dict:
        """Containiner Info for the Latest Model Package"""
        return self.latest_model["ModelPackageDetails"]["InferenceSpecification"]["Containers"][0]

    def model_image(self) -> str:
        """Containiner Image for the Latest Model Package"""
        return self.model_container_info()["Image"]

    def aws_url(self):
        """The AWS URL for looking at/querying this data source"""
        return f"https://{self.aws_region}.console.aws.amazon.com/athena/home"

    def created(self) -> datetime:
        """Return the datetime when this artifact was created"""
        return self.latest_model["CreationTime"]

    def modified(self) -> datetime:
        """Return the datetime when this artifact was last modified"""
        return self.latest_model["CreationTime"]

    def register_endpoint(self, endpoint_name: str):
        """Add this endpoint to the set of registered endpoints for the model

        Args:
            endpoint_name (str): Name of the endpoint
        """
        self.log.important(f"Registering Endpoint {endpoint_name} with Model {self.uuid}...")
        registered_endpoints = set(self.sageworks_meta().get("sageworks_registered_endpoints", []))
        registered_endpoints.add(endpoint_name)
        self.upsert_sageworks_meta({"sageworks_registered_endpoints": list(registered_endpoints)})

        # A new endpoint means we need to refresh our inference path
        time.sleep(2)  # Give the AWS Metadata a chance to update
        self.endpoint_inference_path = self.get_endpoint_inference_path()

    def get_endpoints(self) -> list[str]:
        """Get the list of registered endpoints for this Model

        Returns:
            list[str]: List of registered endpoints
        """
        return self.sageworks_meta().get("sageworks_registered_endpoints", [])

    def get_endpoint_inference_path(self) -> str:
        """Get the S3 Path for the Inference Data"""

        # Look for any Registered Endpoints
        registered_endpoints = self.sageworks_meta().get("sageworks_registered_endpoints")

        # Note: We may have 0 to N endpoints, so we find the one with the most recent artifacts
        if registered_endpoints:
            endpoint_inference_base = self.endpoints_s3_path + "/inference/"
            endpoint_inference_paths = [endpoint_inference_base + e for e in registered_endpoints]
            return newest_files(endpoint_inference_paths, self.sm_session)
        else:
            self.log.warning(f"No registered endpoints found for {self.model_name}!")
            return None

    def target(self) -> Union[str, None]:
        """Return the target for this Model (if supervised, else None)

        Returns:
            str: Target column for this Model (if supervised, else None)
        """
        return self.sageworks_meta().get("sageworks_model_target")  # Returns None if not found

    def features(self) -> Union[list[str], None]:
        """Return a list of features used for this Model

        Returns:
            list[str]: List of features used for this Model
        """
        return self.sageworks_meta().get("sageworks_model_features")  # Returns None if not found

    def class_labels(self) -> Union[list[str], None]:
        """Return the class labels for this Model (if it's a classifier)

        Returns:
            list[str]: List of class labels
        """
        if self.model_type == ModelType.CLASSIFIER:
            return self.sageworks_meta().get("class_labels")  # Returns None if not found
        else:
            return None

    def set_class_labels(self, labels: list[str]):
        """Return the class labels for this Model (if it's a classifier)

        Args:
            labels (list[str]): List of class labels
        """
        if self.model_type == ModelType.CLASSIFIER:
            self.upsert_sageworks_meta({"class_labels": labels})
        else:
            self.log.error(f"Model {self.model_name} is not a classifier!")

    def details(self, recompute=False) -> dict:
        """Additional Details about this Model
        Args:
            recompute (bool, optional): Recompute the details (default: False)
        Returns:
            dict: Dictionary of details about this Model
        """

        # Check if we have cached version of the Model Details
        storage_key = f"model:{self.uuid}:details"
        cached_details = self.data_storage.get(storage_key)
        if cached_details and not recompute:
            return cached_details

        self.log.info("Recomputing Model Details...")
        details = self.summary()
        details["model_type"] = self.model_type.value
        details["model_package_group_arn"] = self.group_arn()
        details["model_package_arn"] = self.model_package_arn()
        aws_meta = self.aws_meta()
        details["description"] = aws_meta.get("ModelPackageDescription", "-")
        details["version"] = aws_meta["ModelPackageVersion"]
        details["status"] = aws_meta["ModelPackageStatus"]
        details["approval_status"] = aws_meta["ModelApprovalStatus"]
        details["image"] = self.model_image().split("/")[-1]  # Shorten the image uri

        # Grab the inference and container info
        package_details = aws_meta["ModelPackageDetails"]
        inference_spec = package_details["InferenceSpecification"]
        container_info = self.model_container_info()
        details["framework"] = container_info.get("Framework", "unknown")
        details["framework_version"] = container_info.get("FrameworkVersion", "unknown")
        details["inference_types"] = inference_spec["SupportedRealtimeInferenceInstanceTypes"]
        details["transform_types"] = inference_spec["SupportedTransformInstanceTypes"]
        details["content_types"] = inference_spec["SupportedContentTypes"]
        details["response_types"] = inference_spec["SupportedResponseMIMETypes"]
        details["model_metrics"] = self.model_metrics()
        if self.model_type == ModelType.CLASSIFIER:
            details["confusion_matrix"] = self.confusion_matrix()
            details["predictions"] = None
        else:
            details["confusion_matrix"] = None
            details["predictions"] = self.get_predictions()

        # Grab the inference metadata
        details["inference_meta"] = self._pull_inference_metadata()

        # Cache the details
        self.data_storage.set(storage_key, details)

        # Return the details
        return details

    def expected_meta(self) -> list[str]:
        """Metadata we expect to see for this Model when it's ready
        Returns:
            list[str]: List of expected metadata keys
        """
        # Our current list of expected metadata, we can add to this as needed
        return ["sageworks_status", "sageworks_training_metrics", "sageworks_training_cm"]

    def is_model_unknown(self) -> bool:
        """Is the Model Type unknown?"""
        return self.model_type == ModelType.UNKNOWN

    def _determine_model_type(self):
        """Internal: Determine the Model Type"""
        model_type = input("Model Type? (classifier, regressor, unsupervised, transformer): ")
        if model_type == "classifier":
            self._set_model_type(ModelType.CLASSIFIER)
        elif model_type == "regressor":
            self._set_model_type(ModelType.REGRESSOR)
        elif model_type == "unsupervised":
            self._set_model_type(ModelType.UNSUPERVISED)
        elif model_type == "transformer":
            self._set_model_type(ModelType.TRANSFORMER)
        else:
            self.log.warning(f"Unknown Model Type {model_type}!")
            self._set_model_type(ModelType.UNKNOWN)

    def onboard(self, interactive=True) -> bool:
        """This is a BLOCKING method that will onboard the Model (make it ready)

        Args:
            interactive (bool, optional): If True, will prompt the user for information. Defaults to True.
        Returns:
            bool: True if the Model is successfully onboarded, False otherwise
        """
        # Set the status to onboarding
        self.set_status("onboarding")

        # Interactive Stuff
        if interactive:
            # Determine the Model Type
            while self.is_model_unknown():
                self._determine_model_type()

            # Determine the Target Column (can be None)
            if self.target() is None:
                target_column = input("Target Column? (for unsupervised/transformer just type None): ")
                if target_column in ["None", "none", ""]:
                    target_column = None
                self.upsert_sageworks_meta({"sageworks_model_target": target_column})

            # Determine the Feature Columns
            if self.features() is None:
                feature_columns = input("Feature Columns? (use commas): ")
                feature_columns = [e.strip() for e in feature_columns.split(",")]
                if feature_columns not in [["None"], ["none"], [""]]:
                    self.upsert_sageworks_meta({"sageworks_model_features": feature_columns})

            # Registered Endpoints?
            if not self.get_endpoints():
                endpoints = input("Register Endpoints? (use commas for multiple): ")
                endpoints = [e.strip() for e in endpoints.split(",")]
                if endpoints not in [["None"], ["none"], [""]]:
                    for endpoint in endpoints:
                        self.log.info(f"Registering Endpoint {endpoint}...")
                        self.register_endpoint(endpoint)

            # Model Owner?
            if self.get_owner() in [None, "unknown"]:
                owner = input("Model Owner: ")
                if owner in ["None", "none", ""]:
                    self.set_owner("unknown")
                else:
                    self.set_owner(owner)

        # Pull the training metrics and inference metrics
        self._pull_training_metrics()
        self._pull_inference_metrics()
        self._pull_inference_cm()

        # Remove the needs_onboard tag
        self.remove_health_tag("needs_onboard")

        # Run a health check and refresh the meta
        time.sleep(2)  # Give the AWS Metadata a chance to update
        self.health_check()
        self.refresh_meta()
        self.details(recompute=True)
        self.set_status("ready")
        return True

    def delete(self):
        """Delete the Model Packages and the Model Group"""

        # If we don't have meta then the model probably doesn't exist
        if self.model_meta is None:
            self.log.info(f"Model {self.model_name} doesn't appear to exist...")
            return

        # First delete the Model Packages within the Model Group
        for model in self.model_meta:
            self.log.info(f"Deleting Model Package {model['ModelPackageArn']}...")
            self.sm_client.delete_model_package(ModelPackageName=model["ModelPackageArn"])

        # Delete the Model Package Group
        self.log.info(f"Deleting Model Group {self.model_name}...")
        self.sm_client.delete_model_package_group(ModelPackageGroupName=self.model_name)

        # Delete any training artifacts
        s3_delete_path = f"{self.model_training_path}"
        self.log.info(f"Deleting Training S3 Objects {s3_delete_path}")
        wr.s3.delete_objects(s3_delete_path, boto3_session=self.boto_session)

        # Delete any data in the Cache
        for key in self.data_storage.list_subkeys(f"model:{self.uuid}"):
            self.log.info(f"Deleting Cache Key {key}...")
            self.data_storage.delete(key)

    def _set_model_type(self, model_type: ModelType):
        """Internal: Set the Model Type for this Model"""
        self.model_type = model_type
        self.upsert_sageworks_meta({"sageworks_model_type": self.model_type.value})
        self.remove_health_tag("model_type_unknown")

    def _get_model_type(self) -> ModelType:
        """Internal: Query the SageWorks Metadata to get the model type
        Returns:
            ModelType: The ModelType of this Model
        Notes:
            This is an internal method that should not be called directly
            Use the model_type attribute instead
        """
        model_type = self.sageworks_meta().get("sageworks_model_type")
        if model_type and model_type != "unknown":
            return ModelType(model_type)
        else:
            self.log.warning(f"Could not determine model type for {self.model_name}!")
            return ModelType.UNKNOWN

    def _pull_training_metrics(self):
        """Internal: Retrieve the training metrics and Confusion Matrix for this model
                     and push the data into the SageWorks Metadata

        Notes:
            This may or may not exist based on whether we have access to TrainingJobAnalytics
        """
        try:
            df = TrainingJobAnalytics(training_job_name=self.training_job_name).dataframe()
            if df.empty:
                self.log.warning(f"No training job metrics found for {self.training_job_name}")
                self.upsert_sageworks_meta({"sageworks_training_metrics": None, "sageworks_training_cm": None})
                return
            if self.model_type == ModelType.REGRESSOR:
                if "timestamp" in df.columns:
                    df = df.drop(columns=["timestamp"])

                # We're going to pivot the DataFrame to get the desired structure
                reg_metrics_df = df.set_index("metric_name").T

                # Store and return the metrics in the SageWorks Metadata
                self.upsert_sageworks_meta(
                    {"sageworks_training_metrics": reg_metrics_df.to_dict(), "sageworks_training_cm": None}
                )
                return

        except (KeyError, botocore.exceptions.ClientError):
            self.log.warning(f"No training job metrics found for {self.training_job_name}")
            # Store and return the metrics in the SageWorks Metadata
            self.upsert_sageworks_meta({"sageworks_training_metrics": None, "sageworks_training_cm": None})
            return

        # We need additional processing for classification metrics
        if self.model_type == ModelType.CLASSIFIER:
            metrics_df, cm_df = self._process_classification_metrics(df)

            # Store and return the metrics in the SageWorks Metadata
            self.upsert_sageworks_meta(
                {"sageworks_training_metrics": metrics_df.to_dict(), "sageworks_training_cm": cm_df.to_dict()}
            )

    def _pull_inference_metrics(self):
        """Internal: Retrieve the inference model metrics for this model
                     and push the data into the SageWorks Metadata

        Notes:
            This may or may not exist based on whether an Endpoint ran Inference
        """
        s3_path = f"{self.endpoint_inference_path}/inference_metrics.csv"
        inference_metrics = pull_s3_data(s3_path)

        # Store data into the SageWorks Metadata
        metrics_storage = None if inference_metrics is None else inference_metrics.to_dict("records")
        self.upsert_sageworks_meta({"sageworks_inference_metrics": metrics_storage})

    def _pull_inference_cm(self) -> Union[pd.DataFrame, None]:
        """Internal: Retrieve the inference Confusion Matrix for this model

        Returns:
            pd.DataFrame: DataFrame of the inference Confusion Matrix (might be None)

        Notes:
            This may or may not exist based on whether an Endpoint ran Inference
        """
        s3_path = f"{self.endpoint_inference_path}/inference_cm.csv"
        inference_cm = pull_s3_data(s3_path, embedded_index=True)

        # Store data into the SageWorks Metadata
        cm_storage = None if inference_cm is None else inference_cm.to_dict("records")
        self.upsert_sageworks_meta({"sageworks_inference_cm": cm_storage})

    def _pull_inference_metadata(self) -> Union[pd.DataFrame, None]:
        """Internal: Retrieve the inference metadata for this model
        Returns:
            dict: Dictionary of the inference metadata (might be None)
        Notes:
            Basically when Endpoint inference was run, name of the dataset, the MD5, etc
        """
        # Sanity check the inference path (which may or may not exist)
        if self.endpoint_inference_path is None:
            return None

        # Pull the inference metadata
        try:
            s3_path = f"{self.endpoint_inference_path}/inference_meta.json"
            return wr.s3.read_json(s3_path)
        except NoFilesFound:
            self.log.info(f"Could not find model inference meta at {s3_path}...")
            return None

    def _extract_training_job_name(self) -> Union[str, None]:
        """Internal: Extract the training job name from the ModelDataUrl"""
        try:
            model_data_url = self.model_container_info()["ModelDataUrl"]
            parsed_url = urllib.parse.urlparse(model_data_url)
            training_job_name = parsed_url.path.lstrip("/").split("/")[0]
            return training_job_name
        except KeyError:
            self.log.warning(f"Could not extract training job name from {model_data_url}")
            return None

    @staticmethod
    def _process_classification_metrics(df: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
        """Internal: Process classification metrics into a more reasonable format
        Args:
            df (pd.DataFrame): DataFrame of training metrics
        Returns:
            (pd.DataFrame, pd.DataFrame): Tuple of DataFrames. Metrics and confusion matrix
        """
        # Split into two DataFrames based on 'metric_name'
        metrics_df = df[df["metric_name"].str.startswith("Metrics:")].copy()
        cm_df = df[df["metric_name"].str.startswith("ConfusionMatrix:")].copy()

        # Split the 'metric_name' into different parts
        metrics_df["class"] = metrics_df["metric_name"].str.split(":").str[1]
        metrics_df["metric_type"] = metrics_df["metric_name"].str.split(":").str[2]

        # Pivot the DataFrame to get the desired structure
        metrics_df = metrics_df.pivot(index="class", columns="metric_type", values="value").reset_index()
        metrics_df = metrics_df.rename_axis(None, axis=1)

        # Now process the confusion matrix
        cm_df["row_class"] = cm_df["metric_name"].str.split(":").str[1]
        cm_df["col_class"] = cm_df["metric_name"].str.split(":").str[2]

        # Pivot the DataFrame to create a form suitable for the heatmap
        cm_df = cm_df.pivot(index="row_class", columns="col_class", values="value")

        # Convert the values in cm_df to integers
        cm_df = cm_df.astype(int)

        return metrics_df, cm_df

    def shapley_values(self) -> Union[list[pd.DataFrame], pd.DataFrame, None]:
        """Retrieve the Shapely values for this model

        Returns:
            pd.DataFrame: Dataframe of the shapley values for the prediction dataframe

        Notes:
            This may or may not exist based on whether an Endpoint ran Shapley
        """

        # Sanity check the inference path (which may or may not exist)
        if self.endpoint_inference_path is None:
            return None

        # Multiple CSV if classifier
        if self.model_type == ModelType.CLASSIFIER:
            # CSVs for shap values are indexed by prediction class
            # Because we don't know how many classes there are, we need to search through
            # a list of S3 objects in the parent folder
            s3_paths = wr.s3.list_objects(self.endpoint_inference_path)
            return [pull_s3_data(f) for f in s3_paths if "inference_shap_values" in f]

        # One CSV if regressor
        if self.model_type == ModelType.REGRESSOR:
            s3_path = f"{self.endpoint_inference_path}/inference_shap_values.csv"
            return pull_s3_data(s3_path)


if __name__ == "__main__":
    """Exercise the ModelCore Class"""

    # Grab a ModelCore object and pull some information from it
    my_model = ModelCore("abalone-regression")

    # Call the various methods

    # Let's do a check/validation of the Model
    print(f"Model Check: {my_model.exists()}")

    # Make sure the model is 'ready'
    my_model.onboard()

    # Get the ARN of the Model Group
    print(f"Model Group ARN: {my_model.group_arn()}")
    print(f"Model Package ARN: {my_model.arn()}")

    # Get the tags associated with this Model
    print(f"Tags: {my_model.get_tags()}")

    # Get the SageWorks metadata associated with this Model
    print(f"SageWorks Meta: {my_model.sageworks_meta()}")

    # Get creation time
    print(f"Created: {my_model.created()}")

    # Get training job name
    print(f"Training Job: {my_model.training_job_name}")

    # Get any captured metrics from the training job
    print("Model Metrics:")
    print(my_model.model_metrics())

    print("Confusion Matrix: (might be None)")
    print(my_model.confusion_matrix())

    # Grab our regression predictions from S3
    print("Captured Predictions: (might be None)")
    print(my_model.get_predictions())

    # Grab our Shapley values from S3
    print("Shapley Values: (might be None)")
    print(my_model.shapley_values())

    # Get the SageWorks metadata associated with this Model
    print(f"SageWorks Meta: {my_model.sageworks_meta()}")

    # Get the latest model object (sagemaker.model.Model)
    sagemaker_model = my_model.latest_model_object()
    print(f"Latest Model Object: {my_model.latest_model_object()}")

    # Get the Class Labels (if it's a classifier)
    my_model = ModelCore("wine-classification")
    print(f"Class Labels: {my_model.class_labels()}")
    my_model.set_class_labels(["red", "white"])
    print(f"Class Labels: {my_model.class_labels()}")

    # Delete the Model
    # my_model.delete()
