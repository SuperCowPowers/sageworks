"""CreateView: An abstract base class for View Creation (training, display, etc)"""

import logging
from typing import Union
from abc import ABC, abstractmethod
import awswrangler as wr

# SageWorks Imports
from sageworks.api import DataSource, FeatureSet
from sageworks.core.artifacts.feature_set_core import FeatureSetCore
from sageworks.core.views.view import View


class CreateView(ABC):
    """CreateView: An abstract base class for View Creation (training, display, etc)"""

    # Class attributes
    log = logging.getLogger("sageworks")

    def __init__(self, view_name: str, artifact: Union[DataSource, FeatureSet], source_table: str = None):
        """CreateView base class constructor

        Args:
            view_name (str): The name of the view
            artifact (Union[DataSource, FeatureSet]): The DataSource or FeatureSet object
            source_table (str, optional): The table/view to create the view from. Defaults to None
        """
        self.view_name = view_name

        # Is this a DataSource or a FeatureSet?
        self.is_feature_set = isinstance(artifact, FeatureSetCore)
        self.auto_id_column = artifact.record_id if self.is_feature_set else None

        # Get the data_source from the artifact
        self.data_source = artifact.data_source if self.is_feature_set else artifact
        self.database = self.data_source.get_database()

        # Set our table names (base, source, and view)
        self.base_table = self.data_source.get_table_name()
        self.source_table = source_table if source_table else self.base_table
        self.view_table_name = f"{self.base_table}_{self.view_name}"

    def create(self, **kwargs) -> Union[View, None]:
        """Create the view, each subclass must implement this method

        Args:
            **kwargs: Additional keyword arguments that are specific to the view type

        Returns:
            Union[View, None]: The created View object (or None if failed to create the view)
        """

        # Create the view
        self.log.important(f"Creating {self.view_name} view {self.view_table_name}...")
        return self.create_impl(self.data_source, **kwargs)

    @abstractmethod
    def create_impl(self, data_source: DataSource, **kwargs) -> Union[View, None]:
        """Abstract Method: Create the view, each subclass must implement this method

        Args:
            data_source (DataSource): A SageWorks DataSource object
            **kwargs: Additional keyword arguments that are specific to the view type

        Returns:
            Union[View, None]: The created View object (or None if failed to create the view)
        """
        pass

    def delete(self):
        """Delete the database view if it exists."""

        # Log the deletion
        self.log.important(f"Dropping View {self.view_table_name}...")
        drop_view_query = f"DROP VIEW {self.view_table_name}"

        # Execute the DROP VIEW query
        try:
            self.data_source.execute_statement(drop_view_query, silence_errors=True)
        except wr.exceptions.QueryFailed as e:
            if "View not found" in str(e):
                self.log.info(f"View {self.view_table_name} not found, this is fine...")
            else:
                raise
