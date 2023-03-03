"""FeatureStore: Helper Class for the AWS Feature Store Service"""
import sys
import argparse
import awswrangler as wr
import json
import logging
from sagemaker.session import Session

# Local Imports
from sageworks.utils.logging import logging_setup
from sageworks.aws_service_connectors.connector import Connector

# Set up logging
logging_setup()


class FeatureStore(Connector):
    def __init__(self):
        """"FeatureStore: Helper Class for the AWS Feature Store Service"""
        self.log = logging.getLogger(__name__)

        # Set up our SageMaker Session and SageMaker Client
        self.sm_session = Session()
        self.sm_client = self.sm_session.boto_session.client("sagemaker")

        # Set up our internal data storage
        self.feature_data = {}

        # Load in the Feature Store Database
        self.refresh()

    def check(self) -> bool:
        """Check if we can reach/connect to this AWS Service"""
        try:
            self.sm_client.list_feature_groups()
            return True
        except Exception as e:
            self.log.critical(f"Error connecting to AWS Feature Store Service: {e}")
            return False

    def refresh(self):
        """Load/reload the tables in the database"""
        # Grab all the Feature Groups in the AWS Feature Store
        print("Reading Feature Store Database...")
        _feature_groups = self.sm_session.boto_session.client("sagemaker").list_feature_groups()['FeatureGroupSummaries']
        _fg_names = [feature_group['FeatureGroupName'] for feature_group in _feature_groups]

        # Get the details for each Feature Group and convert to a data structure with direct lookup
        self.feature_data = {name: self._describe_feature_group(name) for name in _fg_names}

    def get_metadata(self) -> list:
        """Get all the table information in this database"""
        return self.feature_data

    def feature_group_names(self) -> list:
        """Get all the feature group names in this database"""
        return list(self.feature_data.keys())

    def feature_group_details(self, feature_group_name: str) -> dict:
        """Get the details for a specific feature group"""
        return self.feature_data.get(feature_group_name)

    def athena_database_name(self, feature_group_name: str) -> str:
        """Get the Athena Database Name for a specific feature group"""
        return self.feature_data.get(feature_group_name).get('DataCatalogConfig').get('DatabaseName')

    def athena_table_name(self, feature_group_name: str) -> str:
        """Get the Athena Table Name for a specific feature group"""
        return self.feature_data.get(feature_group_name).get('DataCatalogConfig').get('TableName')

    def s3_storage(self, feature_group_name: str) -> str:
        """Get the S3 Location for a specific feature group"""
        return self.feature_data.get(feature_group_name).get('DataCatalogConfig').get('ResolvedOutputS3Uri')

    def get_feature_group_tags(self, feature_group_name: str) -> list:
        """Get the table tag list for the given table name"""
        feature_group = self.get_feature_group_details(feature_group_name)
        return json.loads(feature_group['Parameters'].get('tags', '[]'))

    def set_feature_group_tags(self, table_name: str, tags: list):
        """Set the tags for a specific feature group"""
        wr.catalog.upsert_table_parameters(parameters={'tags': json.dumps(tags)},
                                           database=self.database,
                                           table=table_name)

    def add_feature_group_tags(self, table_name: str, tags: list):
        """Add some the tags for a specific feature set"""
        current_tags = json.loads(wr.catalog.get_table_parameters(self.database, table_name).get('tags'))
        new_tags = list(set(current_tags).union(set(tags)))
        wr.catalog.upsert_table_parameters(parameters={'tags': json.dumps(new_tags)},
                                           database=self.database,
                                           table=table_name)

    def _describe_feature_group(self, feature_group_name: str) -> dict:
        """Internal: Do not call this method directly, use feature_group_details() instead"""
        return self.sm_client.describe_feature_group(FeatureGroupName=feature_group_name)

    def snapshot_query(self, feature_group_name: str) -> str:
        """Construct an Athena 'snapshot' query for the given feature group"""
        database = self.athena_database_name(feature_group_name)
        table = self.athena_table_name(feature_group_name)
        event_time = 'EventTime'
        record_id = 'id'
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


if __name__ == '__main__':
    from pprint import pprint

    # Collect args from the command line
    parser = argparse.ArgumentParser()
    args, commands = parser.parse_known_args()

    # Check for unknown args
    if commands:
        print('Unrecognized args: %s' % commands)
        sys.exit(1)

    # Create the class and get the AWS Data Catalog database info
    feature_store = FeatureStore()

    # List the Feature Groups
    print('Feature Groups:')
    for name in feature_store.get_feature_group_names():
        print(f"\t{name}")

    # Get the details for a specific Feature Group
    my_group = 'AqSolDB-base'
    group_info = feature_store.get_feature_group_details(my_group)
    pprint(group_info)

    # Get the Athena Database Name for this Feature Group
    my_database = feature_store.athena_database_name(my_group)

    # Get the Athena Table Name for this Feature Group
    my_table = feature_store.athena_table_name(my_group)

    # Get the Athena Query for this Feature Group
    my_query = feature_store.snapshot_query(my_group)

    """ TAGS: WIP
    # Get the tags for this Feature Group
    my_tags = feature_store.get_feature_group_tags(my_group)
    print(f"Tags: {my_tags}")

    # Set the tags for this table
    feature_store.set_feature_group_tags(my_group, ['public', 'solubility'])

    # Refresh the connector to get the latest info from AWS Feature Store
    feature_store.refresh()

    # Get the tags for this table
    my_tags = feature_store.get_feature_group_tags(my_group)
    print(f"Tags: {my_tags}")

    # Set the tags for this table
    feature_store.add_feature_group_tags(my_group, ['aqsol', 'smiles'])

    # Refresh the connector to get the latest info from AWS Feature Store
    feature_store.refresh()

    # Get the tags for this table
    tags = feature_store.get_feature_group_tags(my_group)
    print(f"Tags: {tags}")
    """
