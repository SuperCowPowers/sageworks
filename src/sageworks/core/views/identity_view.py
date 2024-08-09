"""IndentityView Class: A View that is a pass-through to the data source table"""

from typing import Union

# SageWorks Imports
from sageworks.api import DataSource
from sageworks.core.views.view import View, ViewType
from sageworks.core.views.view_utils import get_column_list


class IndentityView(View):
    """IndentityView Class: A View that is a pass-through to the data source table"""

    def __init__(self, data_source: DataSource):
        """Initialize the IndentityView

        Args:
            data_source (DataSource): The DataSource object
        """
        self.view_type = ViewType.IDENTITY
        super().__init__(data_source)

    def create_view(self):
        """Create an Identity View: A View that is a pass-through to the data source table"""
        self.log.important("Creating Identity View...")

        # Create the display view table name
        view_name = f"{self.base_table}_identity"

        # Construct the CREATE VIEW query
        create_view_query = f"""
        CREATE OR REPLACE VIEW {view_name} AS
        SELECT * FROM {self.base_table}
        """

        # Execute the CREATE VIEW query
        self.data_source.execute_statement(create_view_query)


if __name__ == "__main__":
    """Exercise the Training View functionality"""
    from sageworks.api import FeatureSet

    # Get the FeatureSet
    fs = FeatureSet("test_features")

    # Create a Identity View
    view = IndentityView(fs.data_source)
    print(view)

    # Pull the display data
    df = view.pull_dataframe()
    print(df.head())
