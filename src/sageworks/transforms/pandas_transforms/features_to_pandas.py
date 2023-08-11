"""FeaturesToPandas: Class to transform a FeatureSet into a Pandas DataFrame"""
import pandas as pd

# Local imports
from sageworks.transforms.transform import Transform, TransformInput, TransformOutput
from sageworks.artifacts.feature_sets.feature_set import FeatureSet


class FeaturesToPandas(Transform):
    """FeaturesToPandas: Class to transform a FeatureSet into a Pandas DataFrame

    Common Usage:
        feature_to_df = FeaturesToPandas(feature_set_uuid)
        feature_to_df.transform(max_rows=<optional max rows to sample>)
        my_df = feature_to_df.get_output()
    """

    def __init__(self, feature_set_name: str):
        """FeaturesToPandas Initialization"""

        # Call superclass init
        super().__init__(input_uuid=feature_set_name, output_uuid="DataFrame")

        # Set up all my instance attributes
        self.input_type = TransformInput.FEATURE_SET
        self.output_type = TransformOutput.PANDAS_DF
        self.output_df = None
        self.transform_run = False

    def transform_impl(self, max_rows=100000):
        """Convert the FeatureSet into a Pandas DataFrame"""

        # Grab the Input (Feature Set)
        input_data = FeatureSet(self.input_uuid)
        if not input_data.exists():
            self.log.critical(f"Feature Set Check on {self.input_uuid} failed!")
            return

        # Grab the table for this Feature Set
        table = input_data.athena_table

        # Get the list of columns (and subtract metadata columns that might get added)
        columns = input_data.column_names()
        filter_columns = ["write_time", "api_invocation_time", "is_deleted"]
        columns = ", ".join([x for x in columns if x not in filter_columns])

        # Get the number of rows in the Feature Set
        num_rows = input_data.num_rows()

        # If the data source has more rows than max_rows, do a sample query
        if num_rows > max_rows:
            percentage = round(max_rows * 100.0 / num_rows)
            self.log.warning(f"DataSource has {num_rows} rows.. sampling down to {max_rows}...")
            query = f'SELECT {columns} FROM "{table}" TABLESAMPLE BERNOULLI({percentage})'
        else:
            query = f'SELECT {columns} FROM "{table}"'

        # Mark the transform as complete and set the output DataFrame
        self.transform_run = True
        self.output_df = input_data.query(query)

    def post_transform(self, **kwargs):
        """Post-Transform: Any checks on the Pandas DataFrame that need to be done"""
        self.log.info("Post-Transform: Checking Pandas DataFrame...")
        self.log.info(f"DataFrame Shape: {self.output_df.shape}")

    def get_output(self) -> pd.DataFrame:
        """Get the DataFrame Output from this Transform"""
        if not self.transform_run:
            self.transform()
        return self.output_df


if __name__ == "__main__":
    """Exercise the FeaturesToPandas Class"""

    # Setup Pandas output options
    pd.set_option("display.max_colwidth", 15)
    pd.set_option("display.max_columns", 15)
    pd.set_option("display.width", 1000)

    # Create the FeatureSet to DF Transform
    feature_to_df = FeaturesToPandas("test-feature-set")

    # Transform the DataSource into a Pandas DataFrame (with max_rows = 1000)
    feature_to_df.transform(max_rows=1000)

    # Grab the output and show it
    my_df = feature_to_df.get_output()
    print(my_df)
