"""MDQView Class: A View that computes various data_quality metrics"""

from typing import Union
import pandas as pd

# SageWorks Imports
from sageworks.api import DataSource, FeatureSet, Model
from sageworks.core.views.view import View
from sageworks.core.views.create_view import CreateView
from sageworks.core.views.view_utils import dataframe_to_table, get_column_list
from sageworks.algorithms.dataframe.row_tagger import RowTagger


class MDQView(CreateView):
    """MDQView Class: A View that computes various data_quality metrics"""

    def __init__(self, artifact: Union[DataSource, FeatureSet]):
        """Initialize the MDQView

        Args:
            artifact (Union[DataSource, FeatureSet]): The DataSource or FeatureSet object
        """
        super().__init__(artifact, "mdq")

    def create_view(self, id_column: str, model: Model, source_table: str = None) -> Union[View, None]:
        """Create a Data Quality View: A View that computes various data_quality metrics

        Args:
            id_column (str): The name of the id column (must be defined for join logic)
            model (Model): The Model object to use for the target and features
            source_table (str, optional): The table/view to create the view from. Defaults to data_source base table.

        Returns:
            Union[View, None]: The created View object (or None if failed to create the view)
        """
        self.log.important(f"Creating Model Data Quality View {self.view_table_name}...")

        # Get the source_table to create the view from
        source_table = source_table if source_table else self.base_table

        # Get the target and feature columns
        target = model.target()
        features = model.features()

        # Check the number of rows in the source_table, if greater than 1M, then give an error and return
        row_count = self.data_source.num_rows()
        if row_count > 1_000_000:
            self.log.error(
                f"Data Quality View cannot be created on more than 1M rows. {source_table} has {row_count} rows."
            )
            return None

        # Drop any columns generated from AWS
        aws_cols = ["write_time", "api_invocation_time", "is_deleted", "event_time"]
        source_table_columns = get_column_list(self.data_source, source_table)
        column_list = [col for col in source_table_columns if col not in aws_cols]

        # Enclose each column name in double quotes
        sql_columns = ", ".join([f'"{column}"' for column in column_list])

        # Pull in the data from the source_table
        query = f"SELECT {sql_columns} FROM {source_table}"
        df = self.data_source.query(query)

        # Check if the id_column exists in the source_table
        if id_column not in df.columns:
            self.log.error(f"id_column {id_column} not found in {source_table}. Cannot create Data Quality View.")
            return None

        # Check if the target column exists in the source_table
        if target not in df.columns:
            self.log.error(f"target column {target} not found in {source_table}. Cannot create Data Quality View.")
            return None

        # Check the type of the target column is categorical (not numeric)
        categorical_target = not pd.api.types.is_numeric_dtype(df[target])

        # Check if the feature columns exist in the source_table
        for feature in features:
            if feature not in df.columns:
                self.log.error(
                    f"feature column {feature} not found in {source_table}. Cannot create Data Quality View."
                )
                return None

        # Now run the RowTagger to compute coincident and high target gradient tags
        row_tagger = RowTagger(
            df,
            features=features,
            id_column=id_column,
            target_column=target,
            within_dist=0.25,
            min_target_diff=1.0,
            outlier_df=self.data_source.outliers(),
            categorical_target=categorical_target,
        )
        dq_df = row_tagger.tag_rows()

        # HACK: These are the columns that are being added to the dataframe
        dq_columns = ["data_quality_tags", "data_quality"]
        dq_df = dq_df.drop(columns=dq_columns, errors="ignore")

        # We're going to rename the tags column to data_quality_tags
        dq_df.rename(columns={"tags": "data_quality_tags"}, inplace=True)

        # We're going to compute a data_quality score based on the tags.
        # Specific/Domain specific logic can be added here.
        # If 'coincident' is in the tags, then the data_quality score is 0.0
        # If 'htg' is in the tags, then the data_quality score is 0.5
        # Else there's no bad tags so the data_quality score is 1.0
        dq_df["data_quality"] = dq_df["data_quality_tags"].apply(
            lambda tags: 0.0 if "coincident" in tags else 0.5 if "htg" in tags else 1.0
        )

        # Just want to keep the new data quality columns
        dq_df = dq_df[dq_columns + [id_column]]

        # Create the data_quality supplemental table
        data_quality_table = f"_{source_table}_data_quality"
        dataframe_to_table(self.data_source, dq_df, data_quality_table)

        # Convert the list of dq_columns into a comma-separated string
        dq_columns_str = ", ".join([f"B.{col}" for col in dq_columns])

        # List the columns from A that are not in B to avoid overlap
        source_columns_str = ", ".join([f"A.{col}" for col in df.columns if col not in dq_columns])

        # Construct the CREATE VIEW query
        create_view_query = f"""
        CREATE OR REPLACE VIEW {self.view_table_name} AS
        SELECT {source_columns_str}, {dq_columns_str}
        FROM {source_table} A
        LEFT JOIN {data_quality_table} B
        ON A.{id_column} = B.{id_column}
        """

        # Execute the CREATE VIEW query
        self.data_source.execute_statement(create_view_query)

        # Return the View
        return View(self.data_source, self.view_name, auto_create=False)


if __name__ == "__main__":
    """Exercise the Training View functionality"""
    from sageworks.api import FeatureSet, Model

    # Get the FeatureSet
    fs = FeatureSet("abalone_features")

    # Get the target and feature columns
    m = Model("abalone-regression")
    target_column = m.target()
    feature_columns = m.features()

    # Create a MDQView
    mdq_view = MDQView(fs).create_view("id", model=m)

    # Pull the data quality dataframe
    my_df = mdq_view.pull_dataframe(head=True)
    print(my_df)

    # Delete the default data_quality view
    mdq_view.delete()
