"""DFToDataSource: Class to publish a Pandas DataFrame as a DataSource"""
import awswrangler as wr
import json
import pandas as pd

# Local imports
from sageworks.utils.logging import logging_setup
from sageworks.transforms.transform import Transform, TransformInput, TransformOutput

# Setup Logging
logging_setup()


class DFToDataSource(Transform):
    def __init__(self):
        """DFToDataSource: Class to publish a Pandas DataFrame as a DataSource"""

        # Call superclass init
        super().__init__()

        # Set up all my class instance vars
        self.input_type = TransformInput.PANDAS_DF
        self.output_type = TransformOutput.DATA_SOURCE
        self.input_df = None

    def transform(self, overwrite: bool = True):
        """Convert the Pandas DataFrame into Parquet Format in the SageWorks S3 Bucket, and
           store the information about the data to the AWS Data Catalog sageworks database"""

        # Add some tags here
        tags = ['sageworks', 'public']

        # Create the Output Parquet file S3 Storage Path
        s3_storage_path = f"{self.data_source_s3_path}/{self.output_uuid}"

        # Write out the DataFrame to Parquet/DataStore/Athena
        wr.s3.to_parquet(self.input_df, path=s3_storage_path, dataset=True, mode='overwrite',
                         database=self.data_catalog_db, table=self.output_uuid,
                         description=f'SageWorks data source: {self.output_uuid}',
                         filename_prefix=f'{self.output_uuid}_',
                         parameters={'tags': json.dumps(tags)},
                         partition_cols=None)  # FIXME: Have some logic around partition columns

    def set_input(self, input_df: pd.DataFrame):
        """Set the DataFrame Input for this Transform"""
        self.input_df = input_df


# Simple test of the DFToDataSource functionality
def test():
    """Test the DFToDataSource Class"""
    from datetime import datetime
    from sageworks.artifacts.data_sources.athena_source import AthenaSource

    # Setup Pandas output options
    pd.set_option('display.max_colwidth', 15)
    pd.set_option('display.max_columns', 15)
    pd.set_option('display.width', 1000)

    # Create some fake data
    fake_data = [
        {'id': 1, 'name': 'sue', 'age': 41, 'score': 7.8, 'date': datetime.now()},
        {'id': 2, 'name': 'bob', 'age': 34, 'score': 6.4, 'date': datetime.now()},
        {'id': 3, 'name': 'ted', 'age': 69, 'score': 8.2, 'date': datetime.now()},
        {'id': 4, 'name': 'bill', 'age': 24, 'score': 5.3, 'date': datetime.now()},
        {'id': 5, 'name': 'sally', 'age': 52, 'score': 9.5, 'date': datetime.now()}
        ]
    fake_df = pd.DataFrame(fake_data)

    # Create my DF to Data Source Transform
    output_uuid = 'test_data'
    df_to_data = DFToDataSource()
    df_to_data.set_input(fake_df)
    df_to_data.set_output_uuid(output_uuid)

    # Store this data into Athena/SageWorks
    df_to_data.transform()

    # Grab the output and query it for a dataframe
    output = AthenaSource(output_uuid)
    df = output.query(f"select * from {output_uuid} limit 5")

    # Show the dataframe
    print(df)


if __name__ == "__main__":
    test()
