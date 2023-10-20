# Inference on an Endpoint
#
# - Pull data from a Test DataSet
# - Run inference on an Endpoint
# - Capture performance metrics in S3 SageWorks Model Bucket

from sageworks.transforms.pandas_transforms.features_to_pandas import FeaturesToPandas
from sageworks.artifacts.models.model import Model
from sageworks.artifacts.endpoints.endpoint import Endpoint
import awswrangler as wr

# Test DatsSet
# There's a couple of options here:
# 1. Grab a SageWorks FeatureSet and pull data from it
# 2. Pull the data from S3 directly

# S3_DATA_PATH = "s3://sageworks-data-science-dev/data-sources/abalone_holdout_2023_10_19.csv"
S3_DATA_PATH = None
FEATURE_SET_NAME = "abalone_feature_set"
FEATURE_SET_NAME = "aqsol_features"
# FEATURE_SET_NAME = None

ENDPOINT_NAME = "abalone-regression-end"
ENDPOINT_NAME = "aqsol-solubility-regression-end"

# These should be filled in
DATA_NAME = "aqsol_holdout_2023_10_19",
DATA_HASH = "12345",
DESCRIPTION = "Test AQSol Data"
TARGET_COLUMN = "solubility"

if S3_DATA_PATH is not None:
    # Read the data from S3
    df = wr.s3.read_csv(S3_DATA_PATH)
else:
    # Grab the FeatureSet
    feature_to_pandas = FeaturesToPandas(FEATURE_SET_NAME)
    feature_to_pandas.transform(max_rows=500)
    df = feature_to_pandas.get_output()

# Spin up our Endpoint
my_endpoint = Endpoint(ENDPOINT_NAME)

# Capture the performance metrics for this Endpoint
my_endpoint.capture_performance_metrics(df, TARGET_COLUMN,
                                        data_name=DATA_NAME,
                                        data_hash=DATA_HASH,
                                        description=DESCRIPTION)

# Important: The Model must explicitly recompute its details
# after the performance metrics are captured
model = Model(my_endpoint.model_name)
model.details(recompute=True)
