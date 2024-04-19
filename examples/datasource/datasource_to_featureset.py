from sageworks.api.data_source import DataSource
from pprint import pprint

# Convert the Data Source to a Feature Set
test_data = DataSource("test_data")
my_features = test_data.to_features()
pprint(my_features.details())
