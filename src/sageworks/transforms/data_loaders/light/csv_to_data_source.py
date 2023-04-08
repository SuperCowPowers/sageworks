"""CSVToDataSource: Class to move local CSV Files into a SageWorks DataSource"""
import pandas as pd
from pandas.errors import ParserError

# Local imports
from sageworks.transforms.transform import Transform, TransformInput, TransformOutput
from sageworks.transforms.pandas_transforms.pandas_to_data import PandasToData


class CSVToDataSource(Transform):
    """CSVToDataSource: Class to move local CSV Files into a SageWorks DataSource"""

    @classmethod
    def info(cls):
        """Print out usage information about CSVToDataSource"""
        print('CSVToDataSource: Class to move local CSV Files into a SageWorks DataSource')
        print('Usage:')
        print('\tcsv_to_data = CSVToDataSource(csv_file_path, data_uuid)')
        print('\tcsv_to_data.set_output_tags(["abalone", "csv", "whatever"])')
        print('\tcsv_to_data.set_output_meta({"sageworks_input": csv_file_path})')
        print('\tcsv_to_data.transform(delete_existing=True/False)')

    def __init__(self, csv_file_path, data_uuid):
        """CSVToDataSource: Class to move local CSV Files into a SageWorks DataSource"""

        # Call superclass init
        super().__init__(csv_file_path, data_uuid)

        # Set up all my instance attributes
        self.input_type = TransformInput.LOCAL_FILE
        self.output_type = TransformOutput.DATA_SOURCE

    def convert_columns_to_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Try to automatically convert object columns to datetime columns"""
        for c in df.columns[df.dtypes == "object"]:  # Look at the object columns
            try:
                df[c] = pd.to_datetime(df[c])
            except (ParserError, ValueError):
                self.log.info(f"Column {c} could not be converted to datetime...")
        return df

    def transform_impl(self, overwrite: bool = True):
        """Convert the local CSV file into Parquet Format in the SageWorks Data Sources Bucket, and
        store the information about the data to the AWS Data Catalog sageworks database"""

        # Read in the Local CSV as a Pandas DataFrame
        df = pd.read_csv(self.input_uuid, low_memory=False)
        df = self.convert_columns_to_datetime(df)

        # Use the SageWorks Pandas to Data Source class
        pandas_to_data = PandasToData(self.output_uuid)
        pandas_to_data.set_input(df)
        pandas_to_data.set_output_tags(self.output_tags)
        pandas_to_data.set_output_meta(self.output_meta)
        pandas_to_data.transform()


if __name__ == "__main__":
    """Exercise the CSVToDataSource Class"""
    import sys
    from pathlib import Path

    # Get the path to the dataset in the repository data directory
    data_path = Path(sys.modules["sageworks"].__file__).parent.parent.parent / "data" / "test_data.csv"

    # Create my Data Loader
    my_loader = CSVToDataSource(data_path, "test_data")
    my_loader.set_output_tags("test:small")
    my_loader.set_output_meta({"sageworks_input": str(data_path)})

    # Store this data as a SageWorks DataSource
    my_loader.transform()
