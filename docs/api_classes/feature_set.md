# FeatureSet
!!! tip inline end "FeatureSet Examples"
    Examples of using the FeatureSet are in the [Examples](#examples) section at the bottom of this page. AWS Feature Store and Feature Groups are quite complicated to set up manually but SageWorks FeatureSet makes it a breeze!
    
::: sageworks.api.feature_set


## Examples
All of the SageWorks Examples are in the Sageworks Repository under the `examples/` directory. For a full code listing of any example please visit our [SageWorks Examples](https://github.com/SuperCowPowers/sageworks/blob/main/examples)

**Create a FeatureSet from a Datasource**

```py title="datasource_to_featureset.py"
from sageworks.api.data_source import DataSource

# Convert the Data Source to a Feature Set
test_data = DataSource('test_data')
my_features = test_data.to_features()
print(my_features.details())
```

**FeatureSet EDA Statistics**

```py title="featureset_eda.py"
from sageworks.api.feature_set import FeatureSet
import pandas as pd

# Grab a FeatureSet and pull some of the EDA Stats
my_features = FeatureSet('test_features')

# Grab some of the EDA Stats
corr_data = my_features.correlations()
corr_df = pd.DataFrame(corr_data)
print(corr_df)

# Get some outliers
outliers = my_features.outliers()
pprint(outliers.head())

# Full set of EDA Stats
eda_stats = my_features.column_stats()
pprint(eda_stats)
```
**Output**

```data
                 age  food_pizza  food_steak  food_sushi  food_tacos    height        id  iq_score
age              NaN   -0.188645   -0.256356    0.263048    0.054211  0.439678 -0.054948 -0.295513
food_pizza -0.188645         NaN   -0.288175   -0.229591   -0.196818 -0.494380  0.137282  0.395378
food_steak -0.256356   -0.288175         NaN   -0.374920   -0.321403 -0.002542 -0.005199  0.076477
food_sushi  0.263048   -0.229591   -0.374920         NaN   -0.256064  0.536396  0.038279 -0.435033
food_tacos  0.054211   -0.196818   -0.321403   -0.256064         NaN -0.091493 -0.051398  0.033364
height      0.439678   -0.494380   -0.002542    0.536396   -0.091493       NaN -0.117372 -0.655210
id         -0.054948    0.137282   -0.005199    0.038279   -0.051398 -0.117372       NaN  0.106020
iq_score   -0.295513    0.395378    0.076477   -0.435033    0.033364 -0.655210  0.106020       NaN

        name     height      weight         salary  age    iq_score  likes_dogs  food_pizza  food_steak  food_sushi  food_tacos outlier_group
0  Person 96  57.582840  148.461349   80000.000000   43  150.000000           1           0           0           0           0    height_low
1  Person 68  73.918663  189.527313  219994.000000   80  100.000000           0           0           0           1           0  iq_score_low
2  Person 49  70.381790  261.237000  175633.703125   49  107.933998           0           0           0           1           0  iq_score_low
3  Person 90  73.488739  193.840698  227760.000000   72  110.821541           1           0           0           0           0   salary_high

<lots of EDA data and statistics>
```

**Create a Model from a FeatureSet**

```py title="featureset_to_model.py"
from sageworks.api.feature_set import FeatureSet
from sageworks.api.model import ModelType
from pprint import pprint

# Grab a FeatureSet
my_features = FeatureSet('test_features')

# Create a Model from the FeatureSet
# Note: For categorical models use ModelType.CATEGORICAL
my_model = my_features.to_model(model_type=ModelType.REGRESSOR, target_column="iq_score")
pprint(my_model.details())
```

**Output**

```data

{'approval_status': 'Approved',
 'content_types': ['text/csv'],
 ...
 'inference_types': ['ml.t2.medium'],
 'input': 'test_features',
 'model_metrics':   metric_name  value
0        RMSE  7.924
1         MAE  6.554,
 'regression_predictions':       iq_score  prediction
0   136.519012  139.964460
1   133.616974  130.819950
2   122.495415  124.967834
3   133.279510  121.010284
4   127.881073  113.825005
    ...
 'response_types': ['text/csv'],
 'sageworks_tags': ['test-model'],
 'shapley_values': None,
 'size': 0.0,
 'status': 'Completed',
 'transform_types': ['ml.m5.large'],
 'uuid': 'test-model',
 'version': 1}
```

## SageWorks UI
Running these few lines of code performs a comprehensive set of Exploratory Data Analysis techniques on your data, pushes the results into AWS, and provides a detailed web visualization of the results.

<figure style="width: 700px;">
<img alt="sageworks_new_light" src="https://github.com/SuperCowPowers/sageworks/assets/4806709/0b4103fe-2c33-4611-86df-ff659fad1a3b">
<figcaption>SageWorks Dashboard: FeatureSets</figcaption>
</figure>


!!! note "Not Finding a particular method?"
    The SageWorks API Classes use 'Core' Classes Internally, so you can lookup all the methods in [SageWorks Core Classes](../core_classes/overview.md)
