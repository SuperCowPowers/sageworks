"""ModelWebView pulls Model metadata from the AWS Service Broker with Details Panels on each Model"""

import pandas as pd

# SageWorks Imports
from sageworks.web_interface.page_views.page_view import PageView
from sageworks.cached.cached_meta import CachedMeta
from sageworks.cached.cached_model import CachedModel
from sageworks.utils.symbols import tag_symbols


class ModelWebView(PageView):
    def __init__(self):
        """ModelWebView pulls Model metadata and populates a Details Panel"""
        # Call SuperClass Initialization
        super().__init__()

        # CachedMeta object for Cloud Platform Metadata
        self.meta = CachedMeta()

        # Initialize the Models DataFrame
        self.models_df = None
        self.refresh()

    def refresh(self):
        """Refresh the model data from the Cloud Platform"""
        self.log.important("Calling refresh()..")
        self.models_df = self.meta.models(details=True)

        # Drop the AWS URL column
        self.models_df.drop(columns=["_aws_url"], inplace=True, errors="ignore")
        # Add Health Symbols to the Model Group Name
        if "Health" in self.models_df.columns:
            self.models_df["Health"] = self.models_df["Health"].map(lambda x: tag_symbols(x))

    def models(self) -> pd.DataFrame:
        """Get all the data that's useful for this view

        Returns:
            pd.DataFrame: DataFrame of the Models View Data
        """
        return self.models_df

    @staticmethod
    def model_details(self, model_uuid: str) -> (dict, None):
        """Get all the details for the given Model UUID
        Args:
            model_uuid(str): The UUID of the Model
        Returns:
            dict: The details for the given Model (or None if not found)
        """
        model = CachedModel(model_uuid)
        if not model.exists():
            return {"Status": "Not Found"}
        elif not model.ready():
            return {"health_tags": model.get_health_tags()}

        # Return the Model Details
        return model.details()


if __name__ == "__main__":
    # Exercising the ModelWebView
    import time
    from pprint import pprint

    # Create the class and get the AWS Model details
    model_view = ModelWebView()

    # List the Models
    print("ModelsSummary:")
    summary = model_view.models()
    print(summary.head())

    # Get the details for the first Model
    my_model_uuid = summary["Model Group"].iloc[0]
    print("\nModelDetails:")
    details = model_view.model_details(my_model_uuid)
    pprint(details)

    # Give any broker threads time to finish
    time.sleep(1)
