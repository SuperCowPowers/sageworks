"""DataToFeaturesLight: Base Class for Light DataSource to FeatureSet using Pandas"""

# Local imports
from sageworks.core.transforms.transform import Transform, TransformInput, TransformOutput
from sageworks.core.transforms.pandas_transforms.data_to_pandas import DataToPandas
from sageworks.core.transforms.pandas_transforms.pandas_to_features import PandasToFeatures
from sageworks.core.artifacts.feature_set_core import FeatureSetCore


class DataToFeaturesLight(Transform):
    """DataToFeaturesLight: Base Class for Light DataSource to FeatureSet using Pandas

    Common Usage:
        ```python
        to_features = DataToFeaturesLight(data_uuid, feature_uuid)
        to_features.set_output_tags(["abalone", "public", "whatever"])
        to_features.transform(id_column="id"/None, event_time_column="date"/None, query=str/None)
        ```
    """

    def __init__(self, data_uuid: str, feature_uuid: str):
        """DataToFeaturesLight Initialization

        Args:
            data_uuid (str): The UUID of the SageWorks DataSource to be transformed
            feature_uuid (str): The UUID of the SageWorks FeatureSet to be created
        """

        # Call superclass init
        super().__init__(data_uuid, feature_uuid)

        # Set up all my instance attributes
        self.input_type = TransformInput.DATA_SOURCE
        self.output_type = TransformOutput.FEATURE_SET
        self.input_df = None
        self.output_df = None

    def pre_transform(self, query: str = None, **kwargs):
        """Pull the input DataSource into our Input Pandas DataFrame
        Args:
            query(str): Optional query to filter the input DataFrame
        """

        # Grab the Input (Data Source)
        data_to_pandas = DataToPandas(self.input_uuid)
        data_to_pandas.transform(query=query)
        self.input_df = data_to_pandas.get_output()

    def transform_impl(self, **kwargs):
        """Transform the input DataFrame into a Feature Set"""

        # This is a reference implementation that should be overridden by the subclass
        self.output_df = self.input_df

    def post_transform(self, id_column=None, event_time_column=None, one_hot_columns=None, **kwargs):
        """At this point the output DataFrame should be populated, so publish it as a Feature Set
        Args:
            id_column(str) Optional: The name of the id column in the output DataFrame (default: None)
            event_time_column(str) Optional: The name of the event time column in the output DataFrame (default: None)
            one_hot_columns(list) Optional: The list of columns to one-hot encode (default: None)
        """
        # Now publish to the output location
        output_features = PandasToFeatures(self.output_uuid)
        output_features.set_input(
            self.output_df, id_column=id_column, event_time_column=event_time_column, one_hot_columns=one_hot_columns
        )
        output_features.set_output_tags(self.output_tags)
        output_features.add_output_meta(self.output_meta)
        output_features.transform()

        # Spin up the FeatureSet and onboard
        fs = FeatureSetCore(self.output_uuid, force_refresh=True)
        fs.onboard()


if __name__ == "__main__":
    """Exercise the DataToFeaturesLight Class"""

    # Create the class with inputs and outputs and invoke the transform
    input_uuid = "test_data"
    output_uuid = "test_features"
    data_to_features = DataToFeaturesLight(input_uuid, output_uuid)
    data_to_features.set_output_tags(["test", "small"])
    data_to_features.transform(id_column="id", event_time_column="date")
