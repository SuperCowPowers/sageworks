"""AWSMeta: A class that provides high level information and summaries of AWS Platform Artifacts.
The AWSMeta class provides 'account' information, configuration, etc. It also provides metadata for
AWS Artifacts, such as Data Sources, Feature Sets, Models, and Endpoints.
"""

import logging
from typing import Union
import pandas as pd
import awswrangler as wr

# SageWorks Imports
from sageworks.core.cloud_platform.abstract_meta import AbstractMeta
from sageworks.utils.datetime_utils import datetime_string
from sageworks.utils.aws_utils import aws_not_found_is_none, aws_throttle, aws_tags_to_dict


class AWSMeta(AbstractMeta):
    """AWSMeta: A class that provides Metadata for a broad set of AWS Platform Artifacts

    Note: This is an internal class, the public API for this class is the 'Meta' class.
          Please see the 'Meta' class for more information.
    """

    def __init__(self):
        """AWSMeta Initialization"""
        self.log = logging.getLogger("sageworks")

        # Call the SuperClass Initialization
        super().__init__()

        # Fill in AWS Specific Information
        self.sageworks_bucket = self.cm.get_config("SAGEWORKS_BUCKET")
        self.incoming_bucket = "s3://" + self.sageworks_bucket + "/incoming-data/"
        self.boto3_session = self.account_clamp.boto3_session
        self.sm_client = self.account_clamp.sagemaker_client()
        self.sm_session = self.account_clamp.sagemaker_session()

    def incoming_data(self) -> pd.DataFrame:
        """Get summary about the incoming raw data.

        Returns:
            pd.DataFrame: A summary of the incoming raw data in the S3 bucket.
        """
        self.log.debug(f"Refreshing metadata for S3 Bucket: {self.incoming_bucket}...")
        s3_file_info = self.s3_describe_objects(self.incoming_bucket)

        # Check if our bucket does not exist
        if s3_file_info is None:
            return pd.DataFrame()

        # Summarize the data into a DataFrame
        data_summary = []
        for full_path, info in s3_file_info.items():
            name = "/".join(full_path.split("/")[-2:]).replace("incoming-data/", "")
            size_mb = f"{info.get('ContentLength', 0) / 1_000_000:.2f} MB"

            summary = {
                "Name": name,
                "Size": size_mb,
                "Modified": datetime_string(info.get("LastModified", "-")),
                "ContentType": info.get("ContentType", "-"),
                "Encryption": info.get("ServerSideEncryption", "-"),
                "Tags": str(info.get("tags", "-")),  # Ensure 'tags' exist if needed
                "_aws_url": self.s3_to_console_url(full_path),
            }
            data_summary.append(summary)
        return pd.DataFrame(data_summary).convert_dtypes()

    def etl_jobs(self) -> pd.DataFrame:
        """Get summary data about Extract, Transform, Load (ETL) Jobs (AWS Glue Jobs)

        Returns:
            pd.DataFrame: A summary of the ETL Jobs deployed in the AWS Platform
        """

        # Retrieve Glue job metadata
        glue_client = self.boto3_session.client("glue")
        response = glue_client.get_jobs()
        jobs = response["Jobs"]

        # Extract relevant data for each job
        job_summary = []
        for job in jobs:
            job_name = job["Name"]
            job_runs = glue_client.get_job_runs(JobName=job_name, MaxResults=1)["JobRuns"]

            last_run = job_runs[0] if job_runs else None
            summary = {
                "Name": job_name,
                "Workers": job.get("NumberOfWorkers", "-"),
                "WorkerType": job.get("WorkerType", "-"),
                "Start Time": datetime_string(last_run["StartedOn"]) if last_run else "-",
                "Duration": f"{last_run['ExecutionTime']} sec" if last_run else "-",
                "State": last_run["JobRunState"] if last_run else "-",
                "_aws_url": self.glue_job_console_url(job_name),
            }
            job_summary.append(summary)

        return pd.DataFrame(job_summary).convert_dtypes()

    def data_sources(self) -> pd.DataFrame:
        """Get a summary of the Data Sources deployed in the AWS Platform

        Returns:
            pd.DataFrame: A summary of the Data Sources deployed in the AWS Platform
        """
        return self._list_catalog_tables("sageworks")

    def views(self, database: str = "sageworks") -> pd.DataFrame:
        """Get a summary of the all the Views, for the given database, in AWS

        Args:
            database (str, optional): Glue database. Defaults to 'sageworks'.

        Returns:
            pd.DataFrame: A summary of all the Views, for the given database, in AWS
        """
        return self._list_catalog_tables(database, views=True)

    def feature_sets(self, details: bool = False) -> pd.DataFrame:
        """Get a summary of the Feature Sets in AWS.

        Args:
            details (bool, optional): Get additional details (Defaults to False).

        Returns:
            pd.DataFrame: A summary of the Feature Sets in AWS.
        """
        # Initialize the SageMaker paginator for listing feature groups
        paginator = self.sm_client.get_paginator("list_feature_groups")
        data_summary = []

        # Use the paginator to retrieve all feature groups
        for page in paginator.paginate():
            for fg in page["FeatureGroupSummaries"]:
                name = fg["FeatureGroupName"]

                # Get details if requested
                feature_set_details = {}
                if details:
                    feature_set_details.update(self.sm_client.describe_feature_group(FeatureGroupName=name))

                # Retrieve SageWorks metadata from tags
                aws_tags = self.get_aws_tags(fg["FeatureGroupArn"])
                summary = {
                    "Feature Group": name,
                    "Created": datetime_string(feature_set_details.get("CreationTime")),
                    "Num Columns": len(feature_set_details.get("FeatureDefinitions", [])),
                    "Input": aws_tags.get("sageworks_input", "-"),
                    "Tags": aws_tags.get("sageworks_tags", "-"),
                    "Online": str(feature_set_details.get("OnlineStoreConfig", {}).get("EnableOnlineStore", "False")),
                    "Offline": str(feature_set_details.get("OfflineStoreConfig", {}).get("EnableGlueDataCatalog", "False")),
                    "_aws_url": self.feature_group_console_url(name),
                }
                data_summary.append(summary)

        # Return the summary as a DataFrame
        return pd.DataFrame(data_summary).convert_dtypes()

    def models(self, details: bool = False) -> pd.DataFrame:
        """Get a summary of the Models in AWS.

        Args:
            details (bool, optional): Get additional details (Defaults to False).

        Returns:
            pd.DataFrame: A summary of the Models in AWS.
        """
        # Initialize the SageMaker paginator for listing model package groups
        paginator = self.sm_client.get_paginator("list_model_package_groups")
        model_summary = []

        # Use the paginator to retrieve all model package groups
        for page in paginator.paginate():
            for group in page["ModelPackageGroupSummaryList"]:
                model_group_name = group["ModelPackageGroupName"]
                created = datetime_string(group["CreationTime"])
                description = group.get("ModelPackageGroupDescription", "-")

                # Initialize variables for details retrieval
                model_details = {}
                aws_tags = {}
                health_tags = "no_health_info"
                status = "Unknown"

                # If details=True get the latest model package details
                if details:
                    latest_model = self.get_latest_model_package_info(model_group_name)
                    if latest_model:
                        model_details.update(self.sm_client.describe_model_package(ModelPackageName=latest_model["ModelPackageArn"]))
                        aws_tags = self.get_aws_tags(group["ModelPackageGroupArn"])
                        health_tags = aws_tags.get("sageworks_health_tags", "no_health_info")
                        status = model_details.get("ModelPackageStatus", "Unknown")
                    else:
                        status = "No Models"

                # Compile model summary
                summary = {
                    "Model Group": model_group_name,
                    "Health": health_tags,
                    "Owner": aws_tags.get("sageworks_owner", "-"),
                    "Model Type": aws_tags.get("sageworks_model_type", "-"),
                    "Created": created,
                    "Ver": model_details.get("ModelPackageVersion", "-"),
                    "Tags": aws_tags.get("sageworks_tags", "-"),
                    "Input": aws_tags.get("sageworks_input", "-"),
                    "Status": status,
                    "Description": description,
                    "_aws_url": self.model_package_group_console_url(model_group_name),
                }
                model_summary.append(summary)

        # Return the summary as a DataFrame
        return pd.DataFrame(model_summary).convert_dtypes()

    def endpoints(self, refresh: bool = False) -> pd.DataFrame:
        """Get a summary of the Endpoints in AWS.

        Args:
            refresh (bool, optional): Force a refresh of the metadata. Defaults to False.

        Returns:
            pd.DataFrame: A summary of the Endpoints in AWS.
        """
        # Initialize the SageMaker client and list all endpoints
        sagemaker_client = self.boto3_session.client("sagemaker")
        paginator = sagemaker_client.get_paginator("list_endpoints")
        data_summary = []

        # Use the paginator to retrieve all endpoints
        for page in paginator.paginate():
            for endpoint in page["Endpoints"]:
                endpoint_name = endpoint["EndpointName"]
                endpoint_info = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)

                # Retrieve SageWorks metadata from tags
                sageworks_meta = self.get_aws_tags(endpoint_info["EndpointArn"])
                health_tags = sageworks_meta.get("sageworks_health_tags") or "no_health_info"

                # Retrieve endpoint configuration to determine instance type or serverless info
                endpoint_config_name = endpoint_info["EndpointConfigName"]
                endpoint_config = sagemaker_client.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
                production_variant = endpoint_config["ProductionVariants"][0]

                # Determine instance type or serverless configuration
                instance_type = production_variant.get("InstanceType")
                if instance_type is None:
                    # If no instance type, it's a serverless configuration
                    mem_size = production_variant["ServerlessConfig"]["MemorySizeInMB"]
                    concurrency = production_variant["ServerlessConfig"]["MaxConcurrency"]
                    mem_in_gb = int(mem_size / 1024)
                    instance_type = f"Serverless ({mem_in_gb}GB/{concurrency})"

                # Compile endpoint summary
                summary = {
                    "Name": endpoint_name,
                    "Health": health_tags,
                    "Instance": instance_type,
                    "Created": datetime_string(endpoint_info.get("CreationTime")),
                    "Tags": sageworks_meta.get("sageworks_tags", "-"),
                    "Input": sageworks_meta.get("sageworks_input", "-"),
                    "Status": endpoint_info["EndpointStatus"],
                    "Variant": production_variant.get("VariantName", "-"),
                    "Capture": str(endpoint_info.get("DataCaptureConfig", {}).get("EnableCapture", "False")),
                    "Samp(%)": str(endpoint_info.get("DataCaptureConfig", {}).get("CurrentSamplingPercentage", "-")),
                }
                data_summary.append(summary)

        # Return the summary as a DataFrame
        return pd.DataFrame(data_summary).convert_dtypes()

    # These are helper methods to construct the AWS URL for the Artifacts
    @staticmethod
    def s3_to_console_url(s3_path: str) -> str:
        """Convert an S3 path to a clickable AWS Console URL."""
        bucket, key = s3_path.replace("s3://", "").split("/", 1)
        return f"https://s3.console.aws.amazon.com/s3/object/{bucket}?prefix={key}"

    def glue_job_console_url(self, job_name: str) -> str:
        """Convert a Glue job name and region into a clickable AWS Console URL."""
        region = self.account_clamp.region
        return f"https://{region}.console.aws.amazon.com/gluestudio/home?region={region}#/editor/job/{job_name}/runs"

    def data_catalog_console_url(self, table_name: str, database: str) -> str:
        """Convert a database and table name to a clickable Athena Console URL."""
        region = self.boto3_session.region_name
        aws = "console.aws.amazon.com"
        return f"https://{region}.{aws}/athena/home?region={region}#query/databases/{database}/tables/{table_name}"

    def feature_group_console_url(self, group_name: str) -> str:
        """Generate an AWS Console URL for a given Feature Group."""
        region = self.boto3_session.region_name
        aws = "console.aws.amazon.com"
        return f"https://{region}.{aws}/sagemaker/home?region={region}#/feature-groups/{group_name}/details"

    def model_package_group_console_url(self, group_name: str) -> str:
        """Generate an AWS Console URL for a given Model Package Group."""
        region = self.boto3_session.region_name
        aws = "console.aws.amazon.com"
        return f"https://{region}.{aws}.com/sagemaker/home?region={region}#/model-registry/{group_name}/details"

    def endpoint_console_url(self, endpoint_name: str) -> str:
        """Generate an AWS Console URL for a given Endpoint."""
        region = self.boto3_session.region_name
        aws = "console.aws.amazon.com"
        return f"https://{region}.{aws}/sagemaker/home?region={region}#/endpoints/{endpoint_name}/details"

    @aws_not_found_is_none
    def s3_describe_objects(self, bucket: str) -> Union[dict, None]:
        """Internal: Get the S3 File Information for the given bucket"""
        return wr.s3.describe_objects(path=bucket, boto3_session=self.boto3_session)

    @aws_throttle
    def get_aws_tags(self, arn: str) -> dict:
        """List the tags for the given AWS ARN"""
        return aws_tags_to_dict(self.sm_session.list_tags(resource_arn=arn))

    @aws_throttle
    def get_latest_model_package_info(self, model_group_name: str) -> Union[dict, None]:
        """Get the latest model package information for the given model group.

        Args:
            model_group_name (str): The name of the model package group.

        Returns:
            dict: The latest model package information.
        """
        model_package_list = self.sm_client.list_model_packages(
            ModelPackageGroupName=model_group_name,
            SortBy="CreationTime",
            SortOrder="Descending",
            MaxResults=1  # Get only the latest model
        )
        # If no model packages are found, return None
        if not model_package_list["ModelPackageSummaryList"]:
            return None

        # Return the latest model package
        return model_package_list["ModelPackageSummaryList"][0]

    def _list_catalog_tables(self, database: str, views: bool = False) -> pd.DataFrame:
        """Internal method to retrieve and summarize Glue catalog tables or views.

        Args:
            database (str): The Glue catalog database name.
            views (bool): If True, filter for views (VIRTUAL_VIEW), otherwise for tables.

        Returns:
            pd.DataFrame: A summary of the tables or views in the specified database.
        """
        self.log.debug(f"Data Catalog Database: {database} for {'views' if views else 'tables'}...")
        all_tables = list(wr.catalog.get_tables(database=database, boto3_session=self.boto3_session))

        # Filter based on whether we're looking for views or tables
        table_type = "VIRTUAL_VIEW" if views else "EXTERNAL_TABLE"
        filtered_tables = [
            table for table in all_tables if not table["Name"].startswith("_") and table["TableType"] == table_type
        ]

        # Summarize the data in a DataFrame
        data_summary = []
        for table in filtered_tables:
            summary = {
                "Name": table["Name"],
                "Database": database,
                "Modified": datetime_string(table["UpdateTime"]),
                "Tags": table.get("Parameters", {}).get("sageworks_tags", "-"),
                "Columns": len(table["StorageDescriptor"].get("Columns", [])),
                "Input": str(
                    table.get("Parameters", {}).get("sageworks_input", "-"),
                ),
                "_aws_url": self.data_catalog_console_url(table["Name"], database),
            }
            data_summary.append(summary)

        return pd.DataFrame(data_summary).convert_dtypes()


if __name__ == "__main__":
    """Exercise the SageWorks AWSMeta Class"""
    from pprint import pprint
    import time

    # Pandas Display Options
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)

    # Create the class
    meta = AWSMeta()

    # Get the AWS Account Info
    print("*** AWS Account ***")
    pprint(meta.account())

    # Get the SageWorks Configuration
    print("*** SageWorks Configuration ***")
    pprint(meta.config())

    # Get the Incoming Data
    print("\n\n*** Incoming Data ***")
    print(meta.incoming_data())

    # Get the AWS Glue Jobs (ETL Jobs)
    print("\n\n*** ETL Jobs ***")
    print(meta.etl_jobs())

    # Get the Data Sources
    print("\n\n*** Data Sources ***")
    print(meta.data_sources())

    # Get the Views (Data Sources)
    print("\n\n*** Views (Data Sources) ***")
    print(meta.views("sageworks"))

    # Get the Views (Feature Sets)
    print("\n\n*** Views (Feature Sets) ***")
    fs_views = meta.views("sagemaker_featurestore")
    print(fs_views)

    # Get the Feature Sets
    print("\n\n*** Feature Sets ***")
    pprint(meta.feature_sets())

    # Get the Models
    print("\n\n*** Models ***")
    start_time = time.time()
    pprint(meta.models())
    print(f"Elapsed Time Model (no details): {time.time() - start_time:.2f}")

    # Get the Models with Details
    print("\n\n*** Models with Details ***")
    start_time = time.time()
    pprint(meta.models(details=True))
    print(f"Elapsed Time Model (with details): {time.time() - start_time:.2f}")

    # Get the Endpoints
    print("\n\n*** Endpoints ***")
    pprint(meta.endpoints())

    # Get the Pipelines
    print("\n\n*** Pipelines ***")
    pprint(meta.pipelines())

    # Now do a deep dive on all the Artifacts
    print("\n\n#")
    print("# Deep Dives ***")
    print("#")
