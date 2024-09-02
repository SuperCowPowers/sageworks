"""ColumnSubsetView Class: Create A View with a subset of columns"""

from typing import Union

# SageWorks Imports
from sageworks.api import DataSource
from sageworks.core.views.create_view import CreateView
from sageworks.core.views.view import View
from sageworks.core.views.view_utils import get_column_list


class ColumnSubsetView(CreateView):
    """ColumnSubsetView Class: Create a View with a subset of columns"""

    def __init__(self):
        """Initialize the ColumnSubsetView"""
        super().__init__()

    def get_view_name(self) -> str:
        """Get the name of the view"""
        return "column_subset"

    def create_view_impl(
        self,
        data_source: DataSource,
        column_list: Union[list[str], None] = None,
        column_limit: int = 30,
    ) -> Union[View, None]:
        """Create the View: A View with a subset of columns

        Args:
            data_source (DataSource): The DataSource object
            column_list (Union[list[str], None], optional): A list of columns to include. Defaults to None.
            column_limit (int, optional): The max number of columns to include. Defaults to 30.

        Returns:
            Union[View, None]: The created View object (or None if failed to create the view)
        """

        # If the user doesn't specify columns, then we'll limit the columns
        if column_list is None:
            # Drop any columns generated from AWS
            aws_cols = ["write_time", "api_invocation_time", "is_deleted", "event_time"]
            source_table_columns = get_column_list(data_source, self.source_table)
            column_list = [col for col in source_table_columns if col not in aws_cols]

            # Limit the number of columns
            column_list = column_list[:column_limit]

        # Enclose each column name in double quotes
        sql_columns = ", ".join([f'"{column}"' for column in column_list])

        # Sanity check the columns
        if not sql_columns:
            self.log.critical(f"{data_source.uuid} No columns to create view...")
            return None

        # Create the view query
        create_view_query = f"""
           CREATE OR REPLACE VIEW {self.view_table_name} AS
           SELECT {sql_columns} FROM {self.source_table}
           """

        # Execute the CREATE VIEW query
        data_source.execute_statement(create_view_query)

        # Return the View
        return View(data_source, self.view_name, auto_create=False)


if __name__ == "__main__":
    """Exercise the Training View functionality"""
    from sageworks.api import FeatureSet

    # Get the FeatureSet
    fs = FeatureSet("test_features")

    # Create a ColumnSubsetView
    column_subset = ColumnSubsetView()
    test_view = column_subset.create_view(fs)

    # Pull the display data
    df = test_view.pull_dataframe()
    print(df.head())

    # Create a Display View with a subset of columns
    columns = ["id", "name", "age", "height", "weight"]
    test_view = column_subset.create_view(fs, column_list=columns)
    print(test_view.pull_dataframe(head=True))
