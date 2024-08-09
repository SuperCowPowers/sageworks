import pytest
import sageworks  # noqa: F401
import logging
from sageworks.utils.test_data_generator import TestDataGenerator
from sageworks.api import DataSource, FeatureSet, Model, Endpoint
from sageworks.aws_service_broker.aws_service_broker import AWSServiceBroker

# Set the logging level
logging.getLogger("sageworks").setLevel(logging.DEBUG)


@pytest.mark.long
def test_data_source_deletion():
    test_data = TestDataGenerator()
    df = test_data.person_data()

    # Create some new data sources
    if not DataSource("abc").exists():
        abc = DataSource(df, name="abc")
    else:
        abc = DataSource("abc")

    if not DataSource("abc_2").exists():
        DataSource(df, name="abc_2")

    # Now Delete the 'shorter' name to see if there's any overlap issues
    abc.delete()


@pytest.mark.long
def test_feature_set_deletion():
    test_data = TestDataGenerator()
    df = test_data.person_data()

    # Make sure the data source exists
    if not DataSource("abc").exists():
        ds = DataSource(df, name="abc")
    else:
        ds = DataSource("abc")

    # If the feature set doesn't exist, create it
    if not FeatureSet("abc_features").exists():
        fs = ds.to_features("abc_features")
    else:
        fs = FeatureSet("abc_features")

    # Now Delete the FeatureSet
    fs.delete()


@pytest.mark.long
def test_endpoint_deletion():

    model = Model("abalone-regression")
    # Create some new endpoints
    if not Endpoint("abc").exists():
        end_abc = model.to_endpoint(name="abc")
    else:
        end_abc = Endpoint("abc")

    if not Endpoint("abc-2").exists():
        model.to_endpoint(name="abc-2")

    # Now Delete the 'shorter' name to see if there's any overlap issues
    end_abc.delete()


if __name__ == "__main__":
    # This forces a refresh on all the data we get from the AWS Broker
    AWSServiceBroker().get_all_metadata(force_refresh=True)

    test_data_source_deletion()
    test_feature_set_deletion()
    test_endpoint_deletion()
