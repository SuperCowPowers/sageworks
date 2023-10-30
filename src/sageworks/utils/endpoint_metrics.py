"""EndpointMetrics is a utility class that fetches metrics for a SageMaker endpoint."""
from datetime import datetime, timedelta, timezone
import pandas as pd

# SageWorks Imports
from sageworks.aws_service_broker.aws_account_clamp import AWSAccountClamp


class EndpointMetrics:
    def __init__(self):
        """
        EndpointMetrics Class
        - Invocations: Number of times the endpoint was invoked.
        - ModelLatency:Time taken by just the model to make a prediction.
        - OverheadLatency: Total time from request until response (does NOT include ModelLatency)
        - ModelSetupTime: Time to launch new compute resources for a serverless endpoint.
        - InvocationModelErrors: The total number of errors (non 200 response codes)
        - Invocation5XXErrors: The number of server error status codes returned.
        - Invocation4XXErrors: The number of client error status codes returned.
        """
        self.aws_account_clamp = AWSAccountClamp()
        self.boto_session = self.aws_account_clamp.boto_session()
        self.cloudwatch = self.boto_session.client("cloudwatch")
        self.start_time = None
        self.end_time = None
        self.metrics = [
            "Invocations",
            "ModelLatency",
            "OverheadLatency",
            "ModelSetupTime",
            "Invocation5XXErrors",
            "Invocation4XXErrors",
        ]
        self.metric_conversions = {
            "Invocations": 1,
            "ModelLatency": 1e-6,
            "OverheadLatency": 1e-6,
            "ModelSetupTime": 1e-6,
            "Invocation5XXErrors": 1,
            "Invocation4XXErrors": 1,
        }
        self.stats = ["Sum", "Average", "Average", "Average", "Sum", "Sum"]

    def get_time_range(self, days_back=7):
        now_utc = datetime.now(timezone.utc)
        self.end_time = now_utc
        self.start_time = self.end_time - timedelta(days=days_back)

        # Convert times to strings that the CloudWatch API expects
        end_time_str = self.end_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        start_time_str = self.start_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        return start_time_str, end_time_str

    def get_metric_data_queries(self, endpoint, days_back=1):
        # Change the Period based on the number of days back
        period = 3600  # Hardcoded to 1 hour for now
        metric_data_queries = []

        for metric_name, stat in zip(self.metrics, self.stats):
            query = {
                "Id": f"m_{metric_name}",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/SageMaker",
                        "MetricName": metric_name,
                        "Dimensions": [
                            {"Name": "EndpointName", "Value": endpoint},
                            {"Name": "VariantName", "Value": "AllTraffic"},
                        ],
                    },
                    "Period": period,
                    "Stat": stat,
                },
                "ReturnData": True,
            }
            metric_data_queries.append(query)

        return metric_data_queries

    def get_metrics(self, endpoint: str, days_back: int = 3) -> pd.DataFrame:
        """Get the metric data for a given endpoint
        Args:
            endpoint(str): The name of the endpoint
            days_back(int): The number of days back to fetch metrics
        Returns:
            pd.DataFrame: The metric data in a dataframe
        """
        # Fetch the metrics
        response = self._fetch_metrics(endpoint=endpoint, days_back=days_back)

        # Parse the response
        metric_data = {}
        for metric in response["MetricDataResults"]:
            metric_name = metric["Label"]

            # Pull timestamps and values
            timestamps = metric["Timestamps"]
            values = metric["Values"]
            values = [round(v * self.metric_conversions[metric_name], 2) for v in values]

            # We're going to add the start and end times to the metric data so that
            # every graph has the same date range (x-axis)
            timestamps.insert(0, self.end_time)
            timestamps.append(self.start_time)
            values.insert(0, 0)
            values.append(0)

            # Create a dataframe and set the index to the timestamps
            metric_data[metric_name] = pd.DataFrame({"timestamps": timestamps, "values": values})
            metric_data[metric_name].set_index("timestamps", inplace=True, drop=True)

        # Now we're going to merge the dataframes
        metric_df = self._merge_dataframes(metric_data=metric_data)
        return metric_df

    @staticmethod
    def _merge_dataframes(metric_data: dict) -> pd.DataFrame:
        """Internal Method: Merge the metric dataframes into a single dataframe
        Args:
            metric_data(dict): The metric data in as a dictionary of dataframes
        Returns:
            pd.DataFrame: The merged metric data
        """
        # Merge DataFrames from the dictionary
        merged_df = pd.DataFrame()
        for metric_name, df in metric_data.items():
            if merged_df.empty:
                merged_df = df.rename(columns={"values": metric_name})
            else:
                merged_df = pd.merge(
                    merged_df,
                    df.rename(columns={"values": metric_name}),
                    left_index=True,
                    right_index=True,
                    how="outer",
                )

        # Sort by index (which is the timestamp)
        merged_df.sort_index(inplace=True)

        # Resample the index to have 1 hour intervals
        merged_df = merged_df.resample("1H").max()

        # Fill NA values with 0 and reset the index (so we can serialize to JSON)
        merged_df.fillna(0, inplace=True)
        merged_df.reset_index(inplace=True)
        return merged_df

    def _fetch_metrics(self, endpoint: str, days_back: int):
        """Internal Method: Fetch metrics from CloudWatch"""
        start_time_str, end_time_str = self.get_time_range(days_back=days_back)
        metric_data_queries = self.get_metric_data_queries(endpoint=endpoint, days_back=days_back)

        response = self.cloudwatch.get_metric_data(
            MetricDataQueries=metric_data_queries, StartTime=start_time_str, EndTime=end_time_str
        )
        return response


if __name__ == "__main__":
    """Exercise the EndpointMetrics class"""
    from pprint import pprint

    # Create the Class and query for metrics
    my_metrics = EndpointMetrics()
    metrics_data = my_metrics.get_metrics(endpoint="abalone-regression-end", days_back=3)
    pprint(metrics_data)
