"""Endpoints: Helper Class for AWS SageMaker Endpoints"""
import sys
import argparse

# SageWorks Imports
from sageworks.aws_service_broker.aws_service_connectors.connector import Connector


class Endpoints(Connector):
    def __init__(self):
        """Endpoints: Helper Class for AWS SageMaker Endpoints"""
        # Call SuperClass Initialization
        super().__init__()

        # Set up our internal data storage
        self.endpoint_data = {}

    def check(self) -> bool:
        """Check if we can reach/connect to this AWS Service"""
        try:
            self.sm_client.list_model_package_groups()
            return True
        except Exception as e:
            self.log.critical(f"Error connecting to AWS Model Registry Service: {e}")
            return False

    def refresh(self):
        """Load/reload the tables in the database"""
        # Grab all the Endpoint Data from SageMaker
        print("Reading Endpoints from SageMaker...")
        _endpoints = self.sm_client.list_endpoints()['Endpoints']
        _end_names = [_endpoint['EndpointName'] for _endpoint in _endpoints]

        # Get the details for each Model Group and convert to a data structure with direct lookup
        self.endpoint_data = {name: self._retrieve_details(name) for name in _end_names}

    def metadata(self) -> dict:
        """Get all the table information in this database"""
        return self.endpoint_data

    def endpoint_names(self) -> list:
        """Get all the feature group names in this database"""
        return list(self.endpoint_data.keys())

    def endpoint_details(self, endpoint_name: str) -> dict:
        """Get the details for a specific feature group"""
        return self.endpoint_data.get(endpoint_name)

    def s3_storage(self, endpoint_name: str) -> str:
        """Get the S3 Location for a specific feature group"""
        return 'TBD Later'

    def _retrieve_details(self, endpoint_name: str) -> dict:
        """Internal: Do not call this method directly, use endpoint_details() instead"""

        # Grab the Model Group details from the AWS Model Registry
        details = self.sm_client.describe_endpoint(EndpointName=endpoint_name)
        return details


if __name__ == '__main__':
    from pprint import pprint

    # Collect args from the command line
    parser = argparse.ArgumentParser()
    args, commands = parser.parse_known_args()

    # Check for unknown args
    if commands:
        print('Unrecognized args: %s' % commands)
        sys.exit(1)

    # Create the class and get the AWS Model Registry details
    my_endpoints = Endpoints()
    my_endpoints.refresh()

    # List the Endpoint Names
    print('Endpoints:')
    for end_name in my_endpoints.endpoint_names():
        print(f"\t{end_name}")

    # Get the details for a specific Endpoint
    endpoint_info = my_endpoints.endpoint_details(end_name)
    pprint(endpoint_info)
