"""DataSourceWebView pulls DataSource metadata from the AWS Service Broker with Details Panels on each DataSource"""
import pandas as pd

# SageWorks Imports
from sageworks.views.artifacts_web_view import ArtifactsWebView
from sageworks.artifacts.data_sources.data_source import DataSource


class DataSourceWebView(ArtifactsWebView):
    def __init__(self):
        """DataSourceWebView pulls DataSource metadata and populates a Details Panel"""
        # Call SuperClass Initialization
        super().__init__()

        # DataFrame of the DataSources Summary
        self.data_sources_df = self.data_sources_summary()

    def refresh(self):
        """Refresh the data from the AWS Service Broker"""
        super().refresh()
        self.data_sources_df = self.data_sources_summary()

    def view_data(self) -> pd.DataFrame:
        """Get all the data that's useful for this view

        Returns:
            pd.DataFrame: DataFrame of the DataSources View Data
        """
        return self.data_sources_df

    def data_source_sample(self, data_source_index: int) -> pd.DataFrame:
        """Get a sample dataframe for the given DataSource Index"""
        data_uuid = self.data_source_name(data_source_index)
        if data_uuid is not None:
            ds = DataSource(data_uuid)
            return ds.sample_df()
        else:
            return pd.DataFrame()

    def data_source_outliers(self, data_source_index: int) -> pd.DataFrame:
        """Get a dataframe of outliers for the given DataSource Index"""
        data_uuid = self.data_source_name(data_source_index)
        if data_uuid is not None:
            ds = DataSource(data_uuid)
            return ds.outliers()
        else:
            return pd.DataFrame()

    def data_source_quartiles(self, data_source_index: int) -> (dict, None):
        """Get all columns quartiles for the given DataSource Index"""
        data_uuid = self.data_source_name(data_source_index)
        if data_uuid is not None:
            return DataSource(data_uuid).quartiles()
        else:
            return None

    def data_source_smart_sample(self, data_source_index: int) -> pd.DataFrame:
        """Get a SMART sample dataframe for the given DataSource Index
        Note:
            SMART here means a sample data + quartiles + outliers for each column"""
        # Sample DataFrame
        sample_rows = self.data_source_sample(data_source_index)

        # Outliers DataFrame
        outlier_rows = self.data_source_outliers(data_source_index)

        # Quartiles Data
        quartiles_data = self.data_source_quartiles(data_source_index)
        if quartiles_data is None:
            return sample_rows

        # Convert the Quartiles Data into a DataFrame
        quartiles_dict_list = dict()
        for col_name, quartiles in quartiles_data.items():
            quartiles_dict_list[col_name] = quartiles.values()
        quartiles_df = pd.DataFrame(quartiles_dict_list)

        # Combine the sample rows with the quartiles data
        return pd.concat([sample_rows, outlier_rows, quartiles_df]).reset_index(drop=True).drop_duplicates()

    def data_source_details(self, data_source_index: int) -> (dict, None):
        """Get all of the details for the given DataSource Index"""
        data_uuid = self.data_source_name(data_source_index)
        if data_uuid is not None:
            ds = DataSource(data_uuid)
            details_data = ds.details()
            details_data["value_counts"] = ds.value_counts()
            return details_data
        else:
            return None

    def data_source_name(self, data_source_index: int) -> (str, None):
        """Helper method for getting the data source name for the given DataSource Index"""
        if not self.data_sources_df.empty and data_source_index < len(self.data_sources_df):
            data_uuid = self.data_sources_df.iloc[data_source_index]["uuid"]
            return data_uuid
        else:
            return None


if __name__ == "__main__":
    # Exercising the DataSourceWebView
    from pprint import pprint

    # Create the class and get the AWS DataSource details
    data_view = DataSourceWebView()

    # List the DataSources
    print("DataSourcesSummary:")
    summary = data_view.view_data()
    print(summary.head())

    # Get the details for the first DataSource
    print("\nDataSourceDetails:")
    details = data_view.data_source_details(0)
    pprint(details)

    # Get a sample dataframe for the given DataSources
    print("\nSampleDataFrame:")
    sample_df = data_view.data_source_smart_sample(0)
    print(sample_df.shape)
    print(sample_df.head())
