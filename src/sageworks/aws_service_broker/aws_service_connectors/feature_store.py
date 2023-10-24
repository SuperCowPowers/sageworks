"""FeatureStore: Helper Class for the AWS Feature Store Service"""
import sys
import argparse

# SageWorks Imports
from sageworks.aws_service_broker.aws_service_connectors.connector import Connector


class FeatureStore(Connector):
    def __init__(self):
        """FeatureStore: Helper Class for the AWS Feature Store Service"""
        # Call SuperClass Initialization
        super().__init__()

        # Set up our internal data storage
        self.feature_data = {}

    def check(self) -> bool:
        """Check if we can reach/connect to this AWS Service"""
        try:
            self.sm_client.list_feature_groups()
            return True
        except Exception as e:
            self.log.critical(f"Error connecting to AWS Feature Store Service: {e}")
            return False

    def refresh_impl(self):
        """Load/reload the tables in the database"""
        # Grab all the Feature Groups in the AWS Feature Store
        _feature_groups = self.sm_client.list_feature_groups()["FeatureGroupSummaries"]
        _fg_names = [feature_group["FeatureGroupName"] for feature_group in _feature_groups]

        # Get the details for each Feature Group and convert to a data structure with direct lookup
        self.feature_data = {name: self._feature_group_details(name) for name in _fg_names}

        # Additional details under the sageworks_meta section for each Feature Group
        for fg_name in _fg_names:
            arn = self.feature_data[fg_name]["FeatureGroupArn"]
            sageworks_meta = self.sageworks_meta_via_arn(arn)
            add_data = {
                "athena_database": self.athena_database_name(fg_name),
                "athena_table": self.athena_table_name(fg_name),
                "s3_storage": self.s3_storage(fg_name),
            }
            sageworks_meta.update(add_data)
            self.feature_data[fg_name]["sageworks_meta"] = sageworks_meta

    def aws_meta(self) -> dict:
        """Return ALL the AWS metadata for this AWS Feature Store"""
        return self.feature_data

    def feature_group_names(self) -> list:
        """Get all the feature group names"""
        return list(self.feature_data.keys())

    def feature_group_details(self, feature_group_name: str) -> dict:
        """Get the details for a specific feature group"""
        return self.feature_data.get(feature_group_name)

    def athena_database_name(self, feature_group_name: str) -> str:
        """Get the Athena Database Name for a specific feature group"""
        try:
            return self.feature_data[feature_group_name]["OfflineStoreConfig"]["DataCatalogConfig"]["Database"].lower()
        except KeyError:
            return "-"

    def athena_table_name(self, feature_group_name: str) -> str:
        """Get the Athena Table Name for a specific feature group"""
        try:
            return self.feature_data[feature_group_name]["OfflineStoreConfig"]["DataCatalogConfig"]["TableName"]
        except KeyError:
            return "-"

    def s3_storage(self, feature_group_name: str) -> str:
        """Get the S3 Location for a specific feature group"""
        return self.feature_data[feature_group_name]["OfflineStoreConfig"]["S3StorageConfig"]["ResolvedOutputS3Uri"]

    def _feature_group_details(self, feature_group_name: str) -> dict:
        """Internal: Do not call this method directly, use feature_group_details() instead"""

        # Grab the Feature Group details from the AWS Feature Store
        details = self.sm_client.describe_feature_group(FeatureGroupName=feature_group_name)
        return details

    def snapshot_query(self, feature_group_name: str) -> str:
        """Construct an Athena 'snapshot' query for the given feature group"""
        database = self.athena_database_name(feature_group_name)
        table = self.athena_table_name(feature_group_name)
        event_time = "event_time"
        record_id = "id"
        query = f"""
            SELECT *
            FROM
                (SELECT *,
                     row_number()
                    OVER (PARTITION BY {record_id}
                ORDER BY  {event_time} desc, Api_Invocation_Time DESC, write_time DESC) AS row_num
                FROM {database}.{table})
            WHERE row_num = 1 and
            NOT is_deleted;
        """
        return query


if __name__ == "__main__":
    from pprint import pprint

    # Collect args from the command line
    parser = argparse.ArgumentParser()
    args, commands = parser.parse_known_args()

    # Check for unknown args
    if commands:
        print("Unrecognized args: %s" % commands)
        sys.exit(1)

    # Create the class and get the AWS Feature Store details
    feature_store = FeatureStore()
    feature_store.refresh()

    # List the Feature Groups
    print("Feature Groups:")
    for fname in feature_store.feature_group_names():
        print(f"\t{fname}")

    # Get the details for a specific Feature Group
    my_group = fname
    group_info = feature_store.feature_group_details(my_group)
    pprint(group_info)

    # Get the Athena Database Name for this Feature Group
    my_database = feature_store.athena_database_name(my_group)

    # Get the Athena Table Name for this Feature Group
    my_table = feature_store.athena_table_name(my_group)

    # Get the Athena Query for this Feature Group
    my_query = feature_store.snapshot_query(my_group)
