"""This Script creates the Classification Artifacts in AWS/SageWorks

DataSources:
    - wine_data
FeatureSets:
    - wine_feature_set
Models:
    - wine-classification
Endpoints:
    - wine-classification-end
"""
import sys

from pathlib import Path
from sageworks.core.artifacts.data_source_factory import DataSourceFactory
from sageworks.core.artifacts.feature_set_core import FeatureSetCore
from sageworks.core.artifacts.model_core import ModelCore, ModelType
from sageworks.core.artifacts.endpoint_core import EndpointCore

from sageworks.core.transforms.data_loaders.light.csv_to_data_source import CSVToDataSource
from sageworks.core.transforms.data_to_features.light.data_to_features_light import DataToFeaturesLight
from sageworks.core.transforms.features_to_model.features_to_model import FeaturesToModel
from sageworks.core.transforms.model_to_endpoint.model_to_endpoint import ModelToEndpoint
from sageworks.aws_service_broker.aws_service_broker import AWSServiceBroker


if __name__ == "__main__":
    # This forces a refresh on all the data we get from the AWs Broker
    AWSServiceBroker().get_all_metadata(force_refresh=True)

    # Get the path to the dataset in the repository data directory
    wine_data_path = Path(sys.modules["sageworks"].__file__).parent.parent.parent / "data" / "wine_dataset.csv"

    # Recreate Flag in case you want to recreate the artifacts
    recreate = False

    # Create the wine_data DataSource
    if recreate or not DataSourceFactory("wine_data").exists():
        my_loader = CSVToDataSource(wine_data_path, "wine_data")
        my_loader.set_output_tags("wine:classification")
        my_loader.transform()

    # Create the wine_features FeatureSet
    if recreate or not FeatureSetCore("wine_features").exists():
        data_to_features = DataToFeaturesLight("wine_data", "wine_features")
        data_to_features.set_output_tags(["wine", "classification"])
        data_to_features.transform(target_column="wine_class", description="Wine Classification Features")

    # Create the wine classification Model
    if recreate or not ModelCore("wine-classification").exists():
        features_to_model = FeaturesToModel("wine_features", "wine-classification", model_type=ModelType.CLASSIFIER)
        features_to_model.set_output_tags(["wine", "classification"])
        features_to_model.transform(target_column="wine_class", description="Wine Classification Model")

    # Create the wine classification Endpoint
    if recreate or not EndpointCore("wine-classification-end").exists():
        model_to_endpoint = ModelToEndpoint("wine-classification", "wine-classification-end")
        model_to_endpoint.set_output_tags(["wine", "classification"])
        model_to_endpoint.transform()
