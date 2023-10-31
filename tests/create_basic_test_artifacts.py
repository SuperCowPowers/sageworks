"""This Script creates the SageWorks Artifacts in AWS needed for the tests

DataSources:
    - test_data
    - abalone_data
FeatureSets:
    - test_feature_set  # Disabled for now
    - abalone_feature_set
Models:
    - abalone-regression
Endpoints:
    - abalone-regression-end
"""
import sys
import time
from pathlib import Path
from sageworks.artifacts.data_sources.data_source import DataSource
from sageworks.artifacts.feature_sets.feature_set import FeatureSet
from sageworks.artifacts.models.model import Model, ModelType
from sageworks.artifacts.endpoints.endpoint import Endpoint

from sageworks.utils.test_data_generator import TestDataGenerator
from sageworks.transforms.pandas_transforms.pandas_to_data import PandasToData
from sageworks.transforms.data_loaders.light.csv_to_data_source import CSVToDataSource
from sageworks.transforms.data_to_features.light.data_to_features_light import DataToFeaturesLight
from sageworks.transforms.features_to_model.features_to_model import FeaturesToModel
from sageworks.transforms.model_to_endpoint.model_to_endpoint import ModelToEndpoint

if __name__ == "__main__":
    # Get the path to the dataset in the repository data directory
    abalone_data_path = Path(sys.modules["sageworks"].__file__).parent.parent.parent / "data" / "abalone.csv"

    # Recreate Flag in case you want to recreate the artifacts
    recreate = False

    # Create the test_data DataSource
    if recreate or not DataSource("test_data").exists():
        # Create a small test data set
        test_data = TestDataGenerator()
        df = test_data.person_data()

        # Create my DF to Data Source Transform
        df_to_data = PandasToData("test_data")
        df_to_data.set_input(df)
        df_to_data.set_output_tags(["test", "small"])
        df_to_data.transform()
        print("Waiting for the test_data to be created...")
        time.sleep(5)

    # Create the abalone_data DataSource
    if recreate or not DataSource("abalone_data").exists():
        my_loader = CSVToDataSource(abalone_data_path, "abalone_data")
        my_loader.set_output_tags("abalone:public")
        my_loader.transform()
        print("Waiting for the abalone_data to be created...")
        time.sleep(5)

    # Create the test_feature_set FeatureSet
    if 0 and recreate or not FeatureSet("test_feature_set").exists():
        data_to_features = DataToFeaturesLight("test_data", "test_feature_set")
        data_to_features.set_output_tags(["test", "small"])
        data_to_features.transform(id_column="id", event_time_column="date")

    # Create the abalone_feature_set FeatureSet
    if recreate or not FeatureSet("abalone_feature_set").exists():
        data_to_features = DataToFeaturesLight("abalone_data", "abalone_feature_set")
        data_to_features.set_output_tags(["abalone", "public"])
        data_to_features.transform(target_column="class_number_of_rings")

    # Create the abalone_regression Model
    if recreate or not Model("abalone-regression").exists():
        features_to_model = FeaturesToModel("abalone_feature_set", "abalone-regression", model_type=ModelType.REGRESSOR)
        features_to_model.set_output_tags(["abalone", "regression"])
        features_to_model.transform(target_column="class_number_of_rings", description="Abalone Regression Model")
        print("Waiting for the Model to be created...")
        time.sleep(10)

    # Create the abalone_regression Endpoint
    if recreate or not Endpoint("abalone-regression-end").exists():
        model_to_endpoint = ModelToEndpoint("abalone-regression", "abalone-regression-end")
        model_to_endpoint.set_output_tags(["abalone", "regression"])
        model_to_endpoint.transform()
