"""EndpointCore: SageWorks EndpointCore Class"""

import time
from datetime import datetime
import botocore
import pandas as pd
import numpy as np
from io import StringIO
import awswrangler as wr
from typing import Union
import shap

# Model Performance Scores
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    mean_squared_error,
    precision_recall_fscore_support,
    median_absolute_error,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.preprocessing import LabelBinarizer

from sagemaker.serializers import CSVSerializer
from sagemaker.deserializers import CSVDeserializer
from sagemaker import Predictor

# SageWorks Imports
from sageworks.core.artifacts.artifact import Artifact
from sageworks.core.artifacts.model_core import ModelCore, ModelType
from sageworks.aws_service_broker.aws_service_broker import ServiceCategory
from sageworks.utils.endpoint_metrics import EndpointMetrics
from sageworks.utils.extract_model_artifact import ExtractModelArtifact


class EndpointCore(Artifact):
    """EndpointCore: SageWorks EndpointCore Class

    Common Usage:
        ```
        my_endpoint = EndpointCore(endpoint_uuid)
        prediction_df = my_endpoint.predict(test_df)
        metrics = my_endpoint.regression_metrics(target_column, prediction_df)
        for metric, value in metrics.items():
            print(f"{metric}: {value:0.3f}")
        ```
    """

    def __init__(self, endpoint_uuid, force_refresh: bool = False):
        """EndpointCore Initialization

        Args:
            endpoint_uuid (str): Name of Endpoint in SageWorks
            force_refresh (bool, optional): Force a refresh of the AWS Broker. Defaults to False.
        """

        # Make sure the endpoint_uuid is compliant
        endpoint_uuid = self.compliant_uuid(endpoint_uuid)

        # Call SuperClass Initialization
        super().__init__(endpoint_uuid)

        # Grab an AWS Metadata Broker object and pull information for Endpoints
        self.endpoint_name = endpoint_uuid
        self.endpoint_meta = self.aws_broker.get_metadata(ServiceCategory.ENDPOINTS, force_refresh=force_refresh).get(
            self.endpoint_name
        )

        # Sanity check that we found the endpoint
        if self.endpoint_meta is None:
            self.log.important(f"Could not find endpoint {self.uuid} within current visibility scope")
            return

        # Sanity check the Endpoint state
        if self.endpoint_meta["EndpointStatus"] == "Failed":
            self.log.critical(f"Endpoint {self.uuid} is in a failed state")
            reason = self.endpoint_meta["FailureReason"]
            self.log.critical(f"Failure Reason: {reason}")
            self.log.critical("Please delete this endpoint and re-deploy...")

        # Set the Inference, Capture, and Monitoring S3 Paths
        self.endpoint_inference_path = self.endpoints_s3_path + "/inference/" + self.uuid
        self.endpoint_data_capture_path = self.endpoints_s3_path + "/data_capture/" + self.uuid
        self.endpoint_monitoring_path = self.endpoints_s3_path + "/monitoring/" + self.uuid

        # Set the Model Name
        self.model_name = self.get_input()

        # This is for endpoint error handling later
        self.endpoint_return_columns = None

        # Call SuperClass Post Initialization
        super().__post_init__()

        # All done
        self.log.info(f"EndpointCore Initialized: {self.endpoint_name}")

    def refresh_meta(self):
        """Refresh the Artifact's metadata"""
        self.endpoint_meta = self.aws_broker.get_metadata(ServiceCategory.ENDPOINTS, force_refresh=True).get(
            self.endpoint_name
        )

    def compliant_uuid(self, uuid: str) -> str:
        """Make sure the uuid is compliant with Athena Table Name requirements

        Args:
            uuid (str): The uuid to make compliant

        Returns:
            str: The compliant uuid
        """
        return self.base_compliant_uuid(uuid, delimiter="-", just_warn=True)

    def exists(self) -> bool:
        """Does the feature_set_name exist in the AWS Metadata?"""
        if self.endpoint_meta is None:
            self.log.debug(f"Endpoint {self.endpoint_name} not found in AWS Metadata")
            return False
        return True

    def health_check(self) -> list[str]:
        """Perform a health check on this model

        Returns:
            list[str]: List of health issues
        """
        if not self.ready():
            return ["needs_onboard"]

        # Call the base class health check
        health_issues = super().health_check()

        # We're going to check for 5xx errors and no activity
        endpoint_metrics = self.endpoint_metrics()

        # Check if we have metrics
        if endpoint_metrics is None:
            health_issues.append("unknown_error")
            return health_issues

        # Check for 5xx errors
        num_errors = endpoint_metrics["Invocation5XXErrors"].sum()
        if num_errors > 5:
            health_issues.append("5xx_errors")
        elif num_errors > 0:
            health_issues.append("5xx_errors_min")
        else:
            self.remove_health_tag("5xx_errors")
            self.remove_health_tag("5xx_errors_min")

        # Check for Endpoint activity
        num_invocations = endpoint_metrics["Invocations"].sum()
        if num_invocations == 0:
            health_issues.append("no_activity")
        else:
            self.remove_health_tag("no_activity")
        return health_issues

    def predict(self, eval_df: pd.DataFrame) -> pd.DataFrame:
        """Run inference/prediction on the given Feature DataFrame
        Args:
            eval_df (pd.DataFrame): DataFrame to run predictions on (must have superset of features)
        Returns:
            pd.DataFrame: Return the DataFrame with additional columns, prediction and any _proba
        """

        # Make sure the eval_df has the features used to train the model
        features = ModelCore(self.model_name).features()
        if not set(features).issubset(eval_df.columns):
            raise ValueError(f"DataFrame does not contain required features: {features}")

        # Create our Endpoint Predictor Class
        predictor = Predictor(
            self.endpoint_name,
            sagemaker_session=self.sm_session,
            serializer=CSVSerializer(),
            deserializer=CSVDeserializer(),
        )

        # Now split up the dataframe into 500 row chunks, send those chunks to our
        # endpoint (with error handling) and stitch all the chunks back together
        df_list = []
        for index in range(0, len(eval_df), 500):
            print("Processing...")

            # Compute partial DataFrames, add them to a list, and concatenate at the end
            partial_df = self._endpoint_error_handling(predictor, eval_df[index : index + 500])
            df_list.append(partial_df)

        # Concatenate the dataframes
        combined_df = pd.concat(df_list, ignore_index=True)

        # Convert data to numeric
        # Note: Since we're using CSV serializers numeric columns often get changed to generic 'object' types

        # Hard Conversion
        # Note: If are string/object columns we want to use 'ignore' here so those columns
        #       won't raise an error (columns maintain current type)
        converted_df = combined_df.apply(pd.to_numeric, errors="ignore")

        # Soft Conversion
        # Convert columns to the best possible dtype that supports the pd.NA missing value.
        converted_df = converted_df.convert_dtypes()

        # Return the Dataframe
        return converted_df

    def is_serverless(self):
        """
        Check if the current endpoint is serverless.
        Returns:
            bool: True if the endpoint is serverless, False otherwise.
        """
        return "Serverless" in self.endpoint_meta["InstanceType"]

    def add_data_capture(self):
        """Add data capture to the endpoint"""
        self.get_monitor().add_data_capture()

    def get_monitor(self):
        """Get the MonitorCore class for this endpoint"""
        from sageworks.core.artifacts.monitor_core import MonitorCore

        return MonitorCore(self.endpoint_name)

    def _endpoint_error_handling(self, predictor, feature_df):
        """Internal: Method that handles Errors, Retries, and Binary Search for Error Row(s)"""

        # Convert the DataFrame into a CSV buffer
        csv_buffer = StringIO()
        feature_df.to_csv(csv_buffer, index=False)

        # Error Handling if the Endpoint gives back an error
        try:
            # Send the CSV Buffer to the predictor
            results = predictor.predict(csv_buffer.getvalue())

            # Construct a DataFrame from the results
            results_df = pd.DataFrame.from_records(results[1:], columns=results[0])

            # Capture the return columns
            self.endpoint_return_columns = results_df.columns.tolist()

            # Return the results dataframe
            return results_df

        except botocore.exceptions.ClientError as err:
            if err.response["Error"]["Code"] == "ModelError":  # Model Error
                # Report the error and raise an exception
                self.log.critical(f"Endpoint prediction error: {err.response.get('Message')}")
                raise err

            # Base case: DataFrame with 1 Row
            if len(feature_df) == 1:
                # If we don't have ANY known good results we're kinda screwed
                if not self.endpoint_return_columns:
                    raise err

                # Construct an Error DataFrame (one row of NaNs in the return columns)
                results_df = self._error_df(feature_df, self.endpoint_return_columns)
                return results_df

            # Recurse on binary splits of the dataframe
            num_rows = len(feature_df)
            split = int(num_rows / 2)
            first_half = self._endpoint_error_handling(predictor, feature_df[0:split])
            second_half = self._endpoint_error_handling(predictor, feature_df[split:num_rows])
            return pd.concat([first_half, second_half], ignore_index=True)

    def _error_df(self, df, all_columns):
        """Internal: Method to construct an Error DataFrame (a Pandas DataFrame with one row of NaNs)"""
        # Create a new dataframe with all NaNs
        error_df = pd.DataFrame(dict(zip(all_columns, [[np.NaN]] * len(self.endpoint_return_columns))))
        # Now set the original values for the incoming dataframe
        for column in df.columns:
            error_df[column] = df[column].values
        return error_df

    def size(self) -> float:
        """Return the size of this data in MegaBytes"""
        return 0.0

    def aws_meta(self) -> dict:
        """Get ALL the AWS metadata for this artifact"""
        return self.endpoint_meta

    def arn(self) -> str:
        """AWS ARN (Amazon Resource Name) for this artifact"""
        return self.endpoint_meta["EndpointArn"]

    def aws_url(self):
        """The AWS URL for looking at/querying this data source"""
        return f"https://{self.aws_region}.console.aws.amazon.com/athena/home"

    def created(self) -> datetime:
        """Return the datetime when this artifact was created"""
        return self.endpoint_meta["CreationTime"]

    def modified(self) -> datetime:
        """Return the datetime when this artifact was last modified"""
        return self.endpoint_meta["LastModifiedTime"]

    def endpoint_metrics(self) -> Union[pd.DataFrame, None]:
        """Return the metrics for this endpoint

        Returns:
            pd.DataFrame: DataFrame with the metrics for this endpoint (or None if no metrics)
        """

        # Do we have it cached?
        metrics_key = f"endpoint:{self.uuid}:endpoint_metrics"
        endpoint_metrics = self.temp_storage.get(metrics_key)
        if endpoint_metrics is not None:
            return endpoint_metrics

        # We don't have it cached so let's get it from CloudWatch
        if "ProductionVariants" not in self.endpoint_meta:
            return None
        self.log.important("Updating endpoint metrics...")
        variant = self.endpoint_meta["ProductionVariants"][0]["VariantName"]
        endpoint_metrics = EndpointMetrics().get_metrics(self.uuid, variant=variant)
        self.temp_storage.set(metrics_key, endpoint_metrics)
        return endpoint_metrics

    def details(self, recompute: bool = False) -> dict:
        """Additional Details about this Endpoint
        Args:
            recompute (bool): Recompute the details (default: False)
        Returns:
            dict(dict): A dictionary of details about this Endpoint
        """
        # Check if we have cached version of the FeatureSet Details
        details_key = f"endpoint:{self.uuid}:details"

        cached_details = self.data_storage.get(details_key)
        if cached_details and not recompute:
            # Update the endpoint metrics before returning cached details
            endpoint_metrics = self.endpoint_metrics()
            cached_details["endpoint_metrics"] = endpoint_metrics
            return cached_details

        # Fill in all the details about this Endpoint
        details = self.summary()

        # Get details from our AWS Metadata
        details["status"] = self.endpoint_meta["EndpointStatus"]
        details["instance"] = self.endpoint_meta["InstanceType"]
        try:
            details["instance_count"] = self.endpoint_meta["ProductionVariants"][0]["CurrentInstanceCount"] or "-"
        except KeyError:
            details["instance_count"] = "-"
        if "ProductionVariants" in self.endpoint_meta:
            details["variant"] = self.endpoint_meta["ProductionVariants"][0]["VariantName"]
        else:
            details["variant"] = "-"

        # Add the underlying model details
        details["model_name"] = self.model_name
        model_details = self.model_details()
        details["model_type"] = model_details.get("model_type", "unknown")
        details["model_metrics"] = model_details.get("model_metrics")
        details["confusion_matrix"] = model_details.get("confusion_matrix")
        details["predictions"] = model_details.get("predictions")
        details["inference_meta"] = model_details.get("inference_meta")

        # Add endpoint metrics from CloudWatch
        details["endpoint_metrics"] = self.endpoint_metrics()

        # Cache the details
        self.data_storage.set(details_key, details)

        # Return the details
        return details

    def onboard(self) -> bool:
        """This is a BLOCKING method that will onboard the Endpoint (make it ready)
        Returns:
            bool: True if the Endpoint is successfully onboarded, False otherwise
        """
        self.log.important(f"Onboarding {self.uuid}...")
        self.set_status("onboarding")
        self.remove_health_tag("needs_onboard")

        # Run a health check and refresh the meta
        time.sleep(2)  # Give the AWS Metadata a chance to update
        self.health_check()
        self.refresh_meta()
        self.details(recompute=True)
        self.set_status("ready")
        return True

    def model_details(self) -> dict:
        """Return the details about the model used in this Endpoint"""
        if self.model_name == "unknown":
            return {}
        else:
            model = ModelCore(self.model_name)
            if model.exists():
                return model.details()
            else:
                return {}

    def model_type(self) -> str:
        """Return the type of model used in this Endpoint"""
        return self.details().get("model_type", "unknown")

    def auto_inference(self, capture: bool = False):
        """Run inference on the endpoint using FeatureSet data

        Args:
            capture (bool, optional): Capture the inference results and metrics (default=False)
        """

        # This Utility needs to be loaded now to avoid circular imports
        from sageworks.utils.endpoint_utils import fs_evaluation_data

        eval_data_df = fs_evaluation_data(self)
        return self.inference(eval_data_df, capture)

    def inference(self, eval_df: pd.DataFrame, capture: bool = False) -> pd.DataFrame:
        """Run inference and compute performance metrics with optional capture

        Args:
            eval_df (pd.DataFrame): DataFrame to run predictions on (must have superset of features)
            capture (bool, optional): Capture the inference results and metrics (default=False)

        Returns:
            pd.DataFrame: DataFrame with the inference results

        Note:
            If capture=True inference/performance metrics are written to S3 Endpoint Inference Folder
        """

        # Run predictions on the evaluation data
        prediction_df = self.predict(eval_df)

        # Get the target column
        target_column = ModelCore(self.model_name).target()

        # Compute the standard performance metrics for this model
        model_type = self.model_type()
        if model_type == ModelType.REGRESSOR.value:
            metrics = self.regression_metrics(target_column, prediction_df)
        elif model_type == ModelType.CLASSIFIER.value:
            metrics = self.classification_metrics(target_column, prediction_df)
        else:
            raise ValueError(f"Unknown Model Type: {model_type}")

        # Print out the metrics
        print(f"Performance Metrics for {self.model_name} on {self.uuid}")
        print(metrics.head())

        # Capture the inference results and metrics
        if capture:
            self._capture_inference_results(prediction_df, target_column, metrics, "Inference Results")

        # Return the prediction DataFrame
        return prediction_df

    def _capture_inference_results(
        self, pred_results_df: pd.DataFrame, target_column: str, metrics: pd.DataFrame, description: str
    ):
        """Internal: Capture the inference results and metrics to S3

        Args:
            pred_results_df (pd.DataFrame): DataFrame with the prediction results
            target_column (str): Name of the target column
            metrics (pd.DataFrame): DataFrame with the performance metrics
            description (str): Description of the inference results
        """

        # Metadata for the model inference
        inference_meta = {
            "test_data": "auto",
            "test_data_hash": "123",
            "test_rows": len(pred_results_df),
            "description": description,
        }

        # Write the metadata dictionary, and metrics to our S3 Model Inference Folder
        wr.s3.to_json(
            pd.DataFrame([inference_meta]),
            f"{self.endpoint_inference_path}/inference_meta.json",
            index=False,
        )
        self.log.debug(f"Writing metrics to {self.endpoint_inference_path}/inference_metrics.csv")
        wr.s3.to_csv(metrics, f"{self.endpoint_inference_path}/inference_metrics.csv", index=False)

        # Write the predictions to our S3 Model Inference Folder (just the target and prediction columns)
        self.log.debug(f"Writing predictions to {self.endpoint_inference_path}/inference_predictions.csv")
        output_columns = [target_column, "prediction"]
        output_columns += [col for col in pred_results_df.columns if col.endswith("_proba")]
        subset_df = pred_results_df[output_columns]
        wr.s3.to_csv(subset_df, f"{self.endpoint_inference_path}/inference_predictions.csv", index=False)

        # CLASSIFIER: Write the confusion matrix to our S3 Model Inference Folder
        model_type = self.model_type()
        if model_type == ModelType.CLASSIFIER.value:
            conf_mtx = self.confusion_matrix(target_column, pred_results_df)
            self.log.debug(f"Writing confusion matrix to {self.endpoint_inference_path}/inference_cm.csv")
            # Note: Unlike other dataframes here, we want to write the index (labels) to the CSV
            wr.s3.to_csv(conf_mtx, f"{self.endpoint_inference_path}/inference_cm.csv", index=True)

        #
        # Generate SHAP values for our Prediction Dataframe
        #

        # Grab the model artifact from AWS
        model_artifact = ExtractModelArtifact(self.endpoint_name).get_model_artifact()

        # Get the exact features used to train the model
        model_features = model_artifact.feature_names_in_
        X_pred = pred_results_df[model_features]

        # Compute the SHAP values
        shap_vals = self.shap_values(model_artifact, X_pred)

        # Multiple shap vals CSV for classifiers
        if model_type == ModelType.CLASSIFIER.value:
            # Need a separate shapley values CSV for each class
            for i, class_shap_vals in enumerate(shap_vals):
                df_shap = pd.DataFrame(class_shap_vals, columns=X_pred.columns)

                # Write shap vals to S3 Model Inference Folder
                shap_file_path = f"{self.endpoint_inference_path}/inference_shap_values_class_{i}.csv"
                self.log.debug(f"Writing SHAP values to {shap_file_path}")
                wr.s3.to_csv(df_shap, shap_file_path, index=False)

        # Single shap vals CSV for regressors
        if model_type == ModelType.REGRESSOR.value:
            # Format shap values into single dataframe
            df_shap = pd.DataFrame(shap_vals, columns=X_pred.columns)

            # Write shap vals to S3 Model Inference Folder
            self.log.debug(f"Writing SHAP values to {self.endpoint_inference_path}/inference_shap_values.csv")
            wr.s3.to_csv(df_shap, f"{self.endpoint_inference_path}/inference_shap_values.csv", index=False)

        # Now recompute the details for our Model
        self.log.important(f"Recomputing Details for {self.model_name} to show latest Inference Results...")
        model = ModelCore(self.model_name)
        model._pull_inference_metrics()
        model.details(recompute=True)

        # Recompute the details so that inference model metrics are updated
        self.log.important(f"Recomputing Details for {self.uuid} to show latest Inference Results...")
        self.details(recompute=True)

    @staticmethod
    def shap_values(model, X: pd.DataFrame) -> np.array:
        """Compute the SHAP values for this Model

        Args:
            model (Model): Model object
            X (pd.DataFrame): DataFrame with the prediction results

        Returns:
            pd.DataFrame: DataFrame with the SHAP values
        """
        # Note: For Tree-based models like decision trees, random forests, XGBoost, LightGBM,
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X)
        return shap_vals

    @staticmethod
    def regression_metrics(target_column: str, prediction_df: pd.DataFrame) -> pd.DataFrame:
        """Compute the performance metrics for this Endpoint
        Args:
            target_column (str): Name of the target column
            prediction_df (pd.DataFrame): DataFrame with the prediction results
        Returns:
            pd.DataFrame: DataFrame with the performance metrics
        """

        # Compute the metrics
        y_true = prediction_df[target_column]
        y_pred = prediction_df["prediction"]

        mae = mean_absolute_error(y_true, y_pred)
        rmse = mean_squared_error(y_true, y_pred, squared=False)
        r2 = r2_score(y_true, y_pred)
        # Mean Absolute Percentage Error
        mape = np.mean(np.where(y_true != 0, np.abs((y_true - y_pred) / y_true), np.abs(y_true - y_pred))) * 100
        # Median Absolute Error
        medae = median_absolute_error(y_true, y_pred)

        # Return the metrics
        return pd.DataFrame.from_records(
            [{"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape, "MedAE": medae, "NumPredRows": len(prediction_df)}]
        )

    def classification_metrics(self, target_column: str, prediction_df: pd.DataFrame) -> pd.DataFrame:
        """Compute the performance metrics for this Endpoint
        Args:
            target_column (str): Name of the target column
            prediction_df (pd.DataFrame): DataFrame with the prediction results
        Returns:
            pd.DataFrame: DataFrame with the performance metrics
        """

        # Get a list of unique labels
        labels = prediction_df[target_column].unique()

        # Calculate scores
        scores = precision_recall_fscore_support(
            prediction_df[target_column], prediction_df["prediction"], average=None, labels=labels
        )

        # Calculate ROC AUC
        # ROC-AUC score measures the model's ability to distinguish between classes;
        # - A value of 0.5 indicates no discrimination (equivalent to random guessing)
        # - A score close to 1 indicates high discriminative power

        # Sanity check for older versions that have a single column for probability
        if "pred_proba" in prediction_df.columns:
            self.log.error("Older version of prediction output detected, rerun inference...")
            roc_auc = [0.0] * len(labels)

        # Convert probability columns to a 2D NumPy array
        else:
            proba_columns = [col for col in prediction_df.columns if col.endswith("_proba")]
            y_score = prediction_df[proba_columns].to_numpy()

            # One-hot encode the true labels
            lb = LabelBinarizer()
            lb.fit(prediction_df[target_column])
            y_true = lb.transform(prediction_df[target_column])

            # Compute ROC AUC
            roc_auc = roc_auc_score(y_true, y_score, multi_class="ovr", average=None)

        # Put the scores into a dataframe
        score_df = pd.DataFrame(
            {
                target_column: labels,
                "precision": scores[0],
                "recall": scores[1],
                "fscore": scores[2],
                "roc_auc": roc_auc,
                "support": scores[3],
            }
        )

        # Sort the target labels
        score_df = score_df.sort_values(by=[target_column], ascending=True)
        return score_df

    def confusion_matrix(self, target_column: str, prediction_df: pd.DataFrame) -> pd.DataFrame:
        """Compute the confusion matrix for this Endpoint
        Args:
            target_column (str): Name of the target column
            prediction_df (pd.DataFrame): DataFrame with the prediction results
        Returns:
            pd.DataFrame: DataFrame with the confusion matrix
        """

        y_true = prediction_df[target_column]
        y_pred = prediction_df["prediction"]

        # Compute the confusion matrix
        conf_mtx = confusion_matrix(y_true, y_pred)

        # Get unique labels
        labels = sorted(list(set(y_true) | set(y_pred)))

        # Create a DataFrame
        conf_mtx_df = pd.DataFrame(conf_mtx, index=labels, columns=labels)
        return conf_mtx_df

    def endpoint_config_name(self) -> str:
        # Grab the Endpoint Config Name from the AWS
        details = self.sm_client.describe_endpoint(EndpointName=self.endpoint_name)
        return details["EndpointConfigName"]

    def delete(self):
        """Delete an existing Endpoint: Underlying Models, Configuration, and Endpoint"""
        self.delete_endpoint_models()

        # Grab the Endpoint Config Name from the AWS
        endpoint_config_name = self.endpoint_config_name()
        try:
            self.log.info(f"Deleting Endpoint Config {endpoint_config_name}...")
            self.sm_client.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
        except botocore.exceptions.ClientError:
            self.log.info(f"Endpoint Config {endpoint_config_name} doesn't exist...")

        # Check for any monitoring schedules
        response = self.sm_client.list_monitoring_schedules(EndpointName=self.uuid)
        monitoring_schedules = response["MonitoringScheduleSummaries"]
        for schedule in monitoring_schedules:
            self.log.info(f"Deleting Endpoint Monitoring Schedule {schedule['MonitoringScheduleName']}...")
            self.sm_client.delete_monitoring_schedule(MonitoringScheduleName=schedule["MonitoringScheduleName"])

        # Delete any inference, data_capture or monitoring artifacts
        for s3_path in [self.endpoint_inference_path, self.endpoint_data_capture_path, self.endpoint_monitoring_path]:
            self.log.info(f"Deleting S3 Path {s3_path}...")
            wr.s3.delete_objects(s3_path, boto3_session=self.boto_session)

        # Now delete any data in the Cache
        for key in self.data_storage.list_subkeys(f"endpoint:{self.uuid}"):
            self.log.info(f"Deleting Cache Key: {key}")
            self.data_storage.delete(key)

        # Okay now delete the Endpoint
        try:
            time.sleep(2)  # Let AWS catch up with any deletions performed above
            self.log.info(f"Deleting Endpoint {self.uuid}...")
            self.sm_client.delete_endpoint(EndpointName=self.uuid)
        except botocore.exceptions.ClientError as e:
            self.log.info("Endpoint ClientError...")
            raise e

    def delete_endpoint_models(self):
        """Delete the underlying Model for an Endpoint"""

        # Grab the Endpoint Config Name from the AWS
        endpoint_config_name = self.endpoint_config_name()

        # Retrieve the Model Names from the Endpoint Config
        try:
            endpoint_config = self.sm_client.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
        except botocore.exceptions.ClientError:
            self.log.info(f"Endpoint Config {self.uuid} doesn't exist...")
            return
        model_names = [variant["ModelName"] for variant in endpoint_config["ProductionVariants"]]
        for model_name in model_names:
            self.log.info(f"Deleting Model {model_name}...")
            try:
                self.sm_client.delete_model(ModelName=model_name)
            except botocore.exceptions.ClientError as error:
                error_code = error.response["Error"]["Code"]
                error_message = error.response["Error"]["Message"]
                if error_code == "ResourceInUse":
                    self.log.warning(f"Model {model_name} is still in use...")
                else:
                    self.log.warning(f"Error: {error_code} - {error_message}")


if __name__ == "__main__":
    """Exercise the Endpoint Class"""
    from sageworks.utils.endpoint_utils import fs_evaluation_data

    # Grab an EndpointCore object and pull some information from it
    my_endpoint = EndpointCore("abalone-regression-end")

    # Let's do a check/validation of the Endpoint
    assert my_endpoint.exists()

    # Creation/Modification Times
    print(my_endpoint.created())
    print(my_endpoint.modified())

    # Get the tags associated with this Endpoint
    print(f"Tags: {my_endpoint.get_tags()}")

    print("Details:")
    print(f"{my_endpoint.details(recompute=True)}")

    # Serverless?
    print(f"Serverless: {my_endpoint.is_serverless()}")

    # Health Check
    print(f"Health Check: {my_endpoint.health_check()}")

    # Run Auto Inference on the Endpoint (uses the FeatureSet)
    print("Running Auto Inference...")
    my_endpoint.auto_inference(capture=False)

    # Run Inference where we provide the data
    # Note: This dataframe could be from a FeatureSet or any other source
    print("Running Inference...")
    eval_df = fs_evaluation_data(my_endpoint)
    pred_results = my_endpoint.inference(eval_df, capture=False)

    # Now set capture=True to save inference results and metrics
    eval_df = fs_evaluation_data(my_endpoint)
    pred_results = my_endpoint.inference(eval_df, capture=True)

    # Run Inference and metrics for a Classification Endpoint
    class_endpoint = EndpointCore("wine-classification-end")
    class_endpoint.auto_inference(capture=True)
