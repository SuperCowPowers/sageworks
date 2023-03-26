"""CSVToDataSource: Class to move local CSV Files into a SageWorks DataSource"""
import pandas as pd

# Local imports
from sageworks.transforms.transform import Transform, TransformInput, TransformOutput
from sageworks.transforms.pandas_transforms.pandas_to_data import PandasToData


class CSVToDataSource(Transform):
    def __init__(self, input_uuid=None, output_uuid=None):
        """CSVToDataSource: Class to move local CSV Files into a SageWorks DataSource"""

        # Call superclass init
        super().__init__(input_uuid, output_uuid)

        # Set up all my instance attributes
        self.input_type = TransformInput.LOCAL_FILE
        self.output_type = TransformOutput.DATA_SOURCE

    def transform_impl(self, overwrite: bool = True):
        """Convert the local CSV file into Parquet Format in the SageWorks Data Sources Bucket, and
           store the information about the data to the AWS Data Catalog sageworks database"""

        # Read in the Local CSV as a Pandas DataFrame
        df = pd.read_csv(self.input_uuid, low_memory=False)

        # Use the SageWorks Pandas to Data Source class
        pandas_to_data = PandasToData(self.output_uuid)
        pandas_to_data.set_input(df)
        pandas_to_data.transform()


# Simple test of the CSVToDataSource functionality
def test():
    """Test the CSVToDataSource Class"""
    import sys
    from pathlib import Path

    # Local/relative path to CSV file (FIXME?)
    data_path = Path(sys.modules['sageworks'].__file__).parent.parent.parent/'data'/'abalone.csv'

    # Create my Data Loader
    my_loader = CSVToDataSource(data_path, 'abalone_data')

    # Store this data as a SageWorks DataSource
    my_loader.transform()


if __name__ == "__main__":
    test()
