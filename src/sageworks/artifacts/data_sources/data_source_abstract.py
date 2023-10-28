"""DataSourceAbstract: Abstract Base Class for all data sources (S3: CSV, JSONL, Parquet, RDS, etc)"""
from abc import abstractmethod
import pandas as pd
from io import StringIO

# SageWorks Imports
from sageworks.artifacts.artifact import Artifact


class DataSourceAbstract(Artifact):
    def __init__(self, uuid):
        """DataSourceAbstract: Abstract Base Class for all data sources (S3: CSV, JSONL, Parquet, RDS, etc)"""

        # Call superclass init
        super().__init__(uuid)

        # Set up our instance attributes
        self._display_columns = None

    @abstractmethod
    def num_rows(self) -> int:
        """Return the number of rows for this Data Source"""
        pass

    @abstractmethod
    def num_columns(self) -> int:
        """Return the number of columns for this Data Source"""
        pass

    @abstractmethod
    def column_names(self) -> list[str]:
        """Return the column names for this Data Source"""
        pass

    @abstractmethod
    def column_types(self) -> list[str]:
        """Return the column types for this Data Source"""
        pass

    def column_details(self) -> dict:
        """Return the column details for this Data Source"""
        return {name: type_ for name, type_ in zip(self.column_names(), self.column_types())}

    def get_display_columns(self) -> list[str]:
        """Set the display columns for this Data Source
        Returns:
            list[str]: The display columns for this Data Source
        """
        if self._display_columns is None and self.num_columns() > 20:
            self.log.important(f"Setting display columns for {self.uuid} to 20 columns...")
            self._display_columns = self.column_names()[:20]
            self._display_columns.append("outlier_group")
        return self._display_columns

    def set_display_columns(self, display_columns: list[str]):
        """Set the display columns for this Data Source
        Args:
            display_columns(list[str]): The display columns for this Data Source
        """
        self._display_columns = display_columns

    def num_display_columns(self) -> int:
        """Return the number of display columns for this Data Source"""
        return len(self._display_columns) if self._display_columns else 0

    @abstractmethod
    def query(self, query: str) -> pd.DataFrame:
        """Query the DataSourceAbstract"""
        pass

    def sample(self, recompute: bool = False) -> pd.DataFrame:
        """Return a sample DataFrame from this DataSource
        Args:
            recompute(bool): Recompute the sample (default: False)
        Returns:
            pd.DataFrame: A sample DataFrame from this DataSource
        """

        # Check if we have a cached sample of rows
        storage_key = f"data_source:{self.uuid}:sample"
        if not recompute and self.data_storage.get(storage_key):
            return pd.read_json(StringIO(self.data_storage.get(storage_key)))

        # No Cache, so we have to compute a sample of data
        self.log.info(f"Sampling {self.uuid}...")
        df = self.sample_impl()
        self.data_storage.set(storage_key, df.to_json())
        return df

    @abstractmethod
    def sample_impl(self) -> pd.DataFrame:
        """Return a sample DataFrame from this DataSourceAbstract
        Returns:
            pd.DataFrame: A sample DataFrame from this DataSource
        """
        pass

    @abstractmethod
    def descriptive_stats(self, recompute: bool = False) -> dict[dict]:
        """Compute Descriptive Stats for all the numeric columns in a DataSource
        Args:
            recompute(bool): Recompute the descriptive stats (default: False)
        Returns:
            dict(dict): A dictionary of descriptive stats for each column in the form
                 {'col1': {'min': 0, 'q1': 1, 'median': 2, 'q3': 3, 'max': 4},
                  'col2': ...}
        """
        pass

    def outliers(self, scale: float = 1.5, recompute: bool = False) -> pd.DataFrame:
        """Return a DataFrame of outliers from this DataSource
        Args:
            scale(float): The scale to use for the IQR (default: 1.5)
            recompute(bool): Recompute the outliers (default: False)
        Returns:
            pd.DataFrame: A DataFrame of outliers from this DataSource
        Notes:
            Uses the IQR * 1.5 (~= 2.5 Sigma) method to compute outliers
            The scale parameter can be adjusted to change the IQR multiplier
        """

        # Check if we have cached outliers
        storage_key = f"data_source:{self.uuid}:outliers"
        if not recompute and self.data_storage.get(storage_key):
            return pd.read_json(StringIO(self.data_storage.get(storage_key)))

        # No Cache, so we have to compute the outliers
        self.log.info(f"Computing Outliers {self.uuid}...")
        df = self.outliers_impl()
        self.data_storage.set(storage_key, df.to_json())
        return df

    @abstractmethod
    def outliers_impl(self, scale: float = 1.5, recompute: bool = False) -> pd.DataFrame:
        """Return a DataFrame of outliers from this DataSource
        Args:
            scale(float): The scale to use for the IQR (default: 1.5)
            recompute(bool): Recompute the outliers (default: False)
        Returns:
            pd.DataFrame: A DataFrame of outliers from this DataSource
        Notes:
            Uses the IQR * 1.5 (~= 2.5 Sigma) method to compute outliers
            The scale parameter can be adjusted to change the IQR multiplier
        """
        pass

    @abstractmethod
    def smart_sample(self) -> pd.DataFrame:
        """Get a SMART sample dataframe from this DataSource
        Returns:
            pd.DataFrame: A combined DataFrame of sample data + outliers
        """
        pass

    @abstractmethod
    def value_counts(self, recompute: bool = False) -> dict[dict]:
        """Compute 'value_counts' for all the string columns in a DataSource
        Args:
            recompute(bool): Recompute the value counts (default: False)
        Returns:
            dict(dict): A dictionary of value counts for each column in the form
                 {'col1': {'value_1': X, 'value_2': Y, 'value_3': Z,...},
                  'col2': ...}
        """
        pass

    @abstractmethod
    def column_stats(self, recompute: bool = False) -> dict[dict]:
        """Compute Column Stats for all the columns in a DataSource
        Args:
            recompute(bool): Recompute the column stats (default: False)
        Returns:
            dict(dict): A dictionary of stats for each column this format
            NB: String columns will NOT have num_zeros and descriptive stats
             {'col1': {'dtype': 'string', 'unique': 4321, 'nulls': 12},
              'col2': {'dtype': 'int', 'unique': 4321, 'nulls': 12, 'num_zeros': 100, 'descriptive_stats': {...}},
              ...}
        """
        pass

    def details(self) -> dict:
        """Additional Details about this DataSourceAbstract Artifact"""
        details = self.summary()
        details["num_rows"] = self.num_rows()
        details["num_columns"] = self.num_columns()
        details["num_display_columns"] = self.num_display_columns()
        details["column_details"] = self.column_details()
        return details

    def expected_meta(self) -> list[str]:
        """DataSources have quite a bit of expected Metadata for EDA displays"""

        # For DataSources, we expect to see the following metadata
        expected_meta = [
            "sageworks_details",
            "sageworks_descriptive_stats",
            "sageworks_value_counts",
            "sageworks_correlations",
            "sageworks_column_stats",
        ]
        return expected_meta

    def ready(self) -> bool:
        """Is the DataSource ready?"""

        # Check if the Artifact is ready
        if not super().ready():
            return False

        # Check if the samples and outliers have been computed
        storage_key = f"data_source:{self.uuid}:sample"
        if not self.data_storage.get(storage_key):
            self.log.warning(f"DataSource {self.uuid} doesn't have sample() calling it...")
            self.sample()
        storage_key = f"data_source:{self.uuid}:outliers"
        if not self.data_storage.get(storage_key):
            self.log.warning(f"DataSource {self.uuid} doesn't have outliers() calling it...")
            self.outliers()

        # Okay so we have the samples and outliers, so we are ready
        return True

    def make_ready(self) -> bool:
        """This is a BLOCKING method that will wait until the Artifact is ready"""
        self.sample()
        self.column_stats()
        self.refresh_meta()  # Refresh the meta since outliers needs descriptive_stats and value_counts
        self.outliers()
        self.details(recompute=True)

        # Lets check if the Artifact is ready
        self.refresh_meta()
        ready = self.ready()
        if ready:
            self.set_status("ready")
            self.refresh_meta()
            return True
        else:
            self.log.critical(f"DataSource {self.uuid} is not ready")
            self.set_status("error")
            return False
