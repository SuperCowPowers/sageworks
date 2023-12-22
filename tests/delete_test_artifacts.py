"""This Script Deletes the SageWorks Artifacts in AWS used for the tests"""
import time
from sageworks.core.artifacts.data_source_factory import DataSourceFactory
from sageworks.core.artifacts.feature_set import FeatureSet
from sageworks.core.artifacts.model import Model
from sageworks.core.artifacts.endpoint_core import EndpointCore
from sageworks.aws_service_broker.aws_service_broker import AWSServiceBroker


if __name__ == "__main__":
    # This forces a refresh on all the data we get from the AWs Broker
    AWSServiceBroker().get_all_metadata(force_refresh=True)

    # Delete the test_data DataSource
    ds = DataSourceFactory("test_data")
    if ds.exists():
        print("Deleting test_data...")
        ds.delete()

    # Delete the abalone_data DataSource
    ds = DataSourceFactory("abalone_data")
    if ds.exists():
        print("Deleting abalone_data...")
        ds.delete()

    # Delete the abalone_data_copy DataSource
    ds = DataSourceFactory("abalone_data_copy")
    if ds.exists():
        print("Deleting abalone_data_copy...")
        ds.delete()

    # Delete the test_feature_set FeatureSet
    fs = FeatureSet("test_feature_set")
    if fs.exists():
        print("Deleting test_feature_set...")
        fs.delete()

    # Delete the abalone_feature_set FeatureSet
    fs = FeatureSet("abalone_feature_set")
    if fs.exists():
        print("Deleting abalone_feature_set...")
        fs.delete()

    # Delete the wine_feature FeatureSet
    fs = FeatureSet("wine_features")
    if fs.exists():
        print("Deleting wine_features...")
        fs.delete()

    # Delete the abalone_regression Model
    m = Model("abalone-regression")
    if m.exists():
        print("Deleting abalone-regression model...")
        m.delete()

    # Delete the abalone_regression Endpoint
    end = EndpointCore("abalone-regression-end")
    if end.exists():
        print("Deleting abalone-regression-end endpoint...")
        end.delete()

    # Classification Artifacts
    fs = FeatureSet("abalone_classification")
    if fs.exists():
        print("Deleting abalone_classification...")
        fs.delete()
    m = Model("abalone-classification")
    if m.exists():
        print("Deleting abalone-classification model...")
        m.delete()
    end = EndpointCore("abalone-classification-end")
    if end.exists():
        print("Deleting abalone-classification-end endpoint...")
        end.delete()

    # Wine Artifacts
    ds = DataSourceFactory("wine_data")
    if ds.exists():
        print("Deleting wine_data...")
        ds.delete()
    fs = FeatureSet("wine_features")
    if fs.exists():
        print("Deleting wine_features...")
        fs.delete()
    m = Model("wine-classification")
    if m.exists():
        print("Deleting wine-classification model...")
        m.delete()
    end = EndpointCore("wine-classification-end")
    if end.exists():
        print("Deleting wine-classification-end endpoint...")
        end.delete()

    # AQSol Artifacts
    ds = DataSourceFactory("aqsol_data")
    if ds.exists():
        print("Deleting aqsol_data...")
        ds.delete()
    fs = FeatureSet("aqsol_features")
    if fs.exists():
        print("Deleting aqsol_features...")
        fs.delete()
    m = Model("aqsol-regression")
    if m.exists():
        print("Deleting aqsol-regression model...")
        m.delete()
    end = EndpointCore("aqsol-regression-end")
    if end.exists():
        print("Deleting aqsol-regression-end endpoint...")
        end.delete()
    fs = FeatureSet("aqsol_rdkit_features")
    if fs.exists():
        print("Deleting aqsol_rdkit_features...")
        fs.delete()
    m = Model("aqsol-rdkit-regression")
    if m.exists():
        print("Deleting aqsol-rdkit-regression model...")
        m.delete()
    end = EndpointCore("aqsol-rdkit-regression-end")
    if end.exists():
        print("Deleting aqsol-rdkit-regression-end endpoint...")
        end.delete()

    time.sleep(5)
    print("All test artifacts should now be deleted!")
