"""ComputationView Class: Create a View with a subset of columns for display purposes"""

from typing import Union

# SageWorks Imports
from sageworks.api import DataSource, FeatureSet
from sageworks.core.views.column_subset_view import ColumnSubsetView


class ComputationView(ColumnSubsetView):
    """ComputationView Class: Create a View with a subset of columns for display purposes"""

    def __init__(self, artifact: Union[DataSource, FeatureSet]):
        """Initialize the ComputationView

        Args:
            artifact (Union[DataSource, FeatureSet]): The DataSource or FeatureSet object
        """
        super().__init__(artifact, "computation")

    def create_view(self, column_list=None, column_limit=30, source_table=None) -> "View":
        """Create the Display View: A View with a subset of columns

        Args:
            column_list (Union[list[str], None], optional): A list of columns to include. Defaults to None.
            column_limit (int, optional): The max number of columns to include. Defaults to 30.
            source_table (str, optional): The table/view to create the view from. Defaults to base table.

        Returns:
            Union[View, None]: The created View object (or None if failed to create the view)
        """
        self.log.important(f"Creating Display View {self.view_table_name}...")
        return super().create_view(column_list, column_limit, source_table)


if __name__ == "__main__":
    """Exercise the Training View functionality"""
    from sageworks.api import FeatureSet
    
    # Get the FeatureSet
    fs = FeatureSet("test_features")

    # Create a ComputationView
    view_maker = ComputationView(fs)
    compute_view = view_maker.create_view()

    # Pull the computation data
    df = compute_view.pull_dataframe()
    print(df.head())
