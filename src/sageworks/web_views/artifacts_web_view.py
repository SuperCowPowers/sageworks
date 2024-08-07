"""ArtifactsWebView pulls All the metadata from the AWS Service Broker and organizes/summarizes it"""

import pandas as pd

# SageWorks Imports
from sageworks.web_views.artifacts_text_view import ArtifactsTextView
from sageworks.utils.symbols import tag_symbols


class ArtifactsWebView(ArtifactsTextView):
    def __init__(self):
        """ArtifactsWebView pulls All the metadata from the AWS Service Broker and organizes/summarizes it"""
        # Call SuperClass Initialization
        super().__init__()

    def incoming_data_summary(self, add_hyperlinks: bool = True) -> pd.DataFrame:
        """Get summary data about the AWS Glue Jobs

        Args:
            add_hyperlinks (bool): Whether to add hyperlinks to the Name column

        Returns:
            pd.DataFrame: Summary data about the AWS Glue Jobs
        """

        # We get the dataframe from the ArtifactsTextView
        s3_data_df = super().incoming_data_summary()

        # We might get an empty dataframe
        if s3_data_df.empty:
            return s3_data_df

        # Add a UUID column
        s3_data_df["uuid"] = s3_data_df["Name"]

        # Pull the AWS URLs and construct some hyperlinks
        if add_hyperlinks:
            hyperlinked_names = []
            for name, aws_url in zip(s3_data_df["Name"], s3_data_df["_aws_url"]):
                hyperlinked_names.append(self.hyperlinks(name, "glue_jobs", aws_url))
            s3_data_df["Name"] = hyperlinked_names

        # Drop the AWS URL column and return the dataframe
        s3_data_df.drop(columns=["_aws_url"], inplace=True)
        return s3_data_df

    def glue_jobs_summary(self, add_hyperlinks: bool = True) -> pd.DataFrame:
        """Get summary data about the AWS Glue Jobs

        Args:
            add_hyperlinks (bool): Whether to add hyperlinks to the Name column

        Returns:
            pd.DataFrame: Summary data about the AWS Glue Jobs
        """

        # We get the dataframe from the ArtifactsTextView
        glue_df = super().glue_jobs_summary()

        # We might get an empty dataframe
        if glue_df.empty:
            return glue_df

        # Add a UUID column
        glue_df["uuid"] = glue_df["Name"]

        # Pull the AWS URLs and construct some hyperlinks
        if add_hyperlinks:
            hyperlinked_names = []
            for name, aws_url in zip(glue_df["Name"], glue_df["_aws_url"]):
                hyperlinked_names.append(self.hyperlinks(name, "glue_jobs", aws_url))
            glue_df["Name"] = hyperlinked_names

        # Drop the AWS URL column and return the dataframe
        glue_df.drop(columns=["_aws_url"], inplace=True)
        return glue_df

    def data_sources_summary(self, add_hyperlinks: bool = True) -> pd.DataFrame:
        """Get summary data about the SageWorks DataSources

        Args:
            add_hyperlinks (bool): Whether to add hyperlinks to the Name column

        Returns:
            pd.DataFrame: Summary data about the SageWorks DataSources
        """

        # We get the dataframe from the ArtifactsTextView
        data_df = super().data_sources_summary()

        # We might get an empty dataframe
        if data_df.empty:
            return data_df

        # Add a UUID column
        data_df["uuid"] = data_df["Name"]

        # Pull the AWS URLs and construct some hyperlinks
        if add_hyperlinks:
            hyperlinked_names = []
            for name, aws_url in zip(data_df["Name"], data_df["_aws_url"]):
                hyperlinked_names.append(self.hyperlinks(name, "data_sources", aws_url))
            data_df["Name"] = hyperlinked_names

        # Drop the AWS URL column and return the dataframe
        data_df.drop(columns=["_aws_url"], inplace=True)
        return data_df

    def feature_sets_summary(self, add_hyperlinks: bool = True) -> pd.DataFrame:
        """Get summary data about the SageWorks FeatureSets

        Args:
            add_hyperlinks (bool): Whether to add hyperlinks to the Feature Group column

        Returns:
            pd.DataFrame: Summary data about the SageWorks FeatureSets
        """

        # We get the dataframe from the ArtifactsTextView
        feature_df = super().feature_sets_summary()

        # We might get an empty dataframe
        if feature_df.empty:
            return feature_df

        # Add a UUID column
        feature_df["uuid"] = feature_df["Feature Group"]

        # Pull the AWS URLs and construct some hyperlinks
        if add_hyperlinks:
            hyperlinked_names = []
            for group_name, aws_url in zip(feature_df["Feature Group"], feature_df["_aws_url"]):
                hyperlinked_names.append(self.hyperlinks(group_name, "feature_sets", aws_url))
            feature_df["Feature Group"] = hyperlinked_names

        # Drop the AWS URL column and return the dataframe
        feature_df.drop(columns=["_aws_url"], inplace=True)
        return feature_df

    def models_summary(self, add_hyperlinks: bool = True) -> pd.DataFrame:
        """Get summary data about the SageWorks Models

        Args:
            add_hyperlinks (bool): Whether to add hyperlinks to the Model Group column

        Returns:
            pd.DataFrame: Summary data about the SageWorks Models
        """

        # We get the dataframe from the ArtifactsTextView and hyperlink the Model Group column
        model_df = super().models_summary()

        # We might get an empty dataframe
        if model_df.empty:
            return model_df

        # Add a UUID column
        model_df["uuid"] = model_df["Model Group"]
        if add_hyperlinks:
            model_df["Model Group"] = model_df["Model Group"].map(lambda x: self.hyperlinks(x, "models", ""))

        # Add Health Symbols to the Model Group Name
        if "Health" in model_df.columns:
            model_df["Health"] = model_df["Health"].map(lambda x: tag_symbols(x))

        return model_df

    def endpoints_summary(self, add_hyperlinks: bool = True) -> pd.DataFrame:
        """Get summary data about the SageWorks Endpoints

        Args:
            add_hyperlinks (bool): Whether to add hyperlinks to the Name column

        Returns:
            pd.DataFrame: Summary data about the SageWorks Endpoints
        """

        # We get the dataframe from the ArtifactsTextView and hyperlink the Name column
        endpoint_df = super().endpoints_summary()

        # We might get an empty dataframe
        if endpoint_df.empty:
            return endpoint_df

        # Add a UUID column
        endpoint_df["uuid"] = endpoint_df["Name"]
        if add_hyperlinks:
            endpoint_df["Name"] = endpoint_df["Name"].map(lambda x: self.hyperlinks(x, "endpoints", ""))

        # Add Health Symbols to the Endpoint Name
        if "Health" in endpoint_df.columns:
            endpoint_df["Health"] = endpoint_df["Health"].map(lambda x: tag_symbols(x))

        return endpoint_df

    @staticmethod
    def hyperlinks(name, detail_type, aws_url):
        """Construct a hyperlink for the given name and detail_type"""
        if detail_type == "glue_jobs":
            return f"<a href='{aws_url}' target='_blank'>{name}</a>"

        # Other types have both a detail page and a query page
        link = f"<a href='{detail_type}' target='_blank'>{name}</a>"
        if aws_url:
            link += f" [<a href='{aws_url}' target='_blank'>query</a>]"
        return link


if __name__ == "__main__":
    import time

    # Create the class and get the AWS Model Registry details
    artifact_view = ArtifactsWebView()

    # List the Endpoint Names
    print("ArtifactsWebView:")
    for category, df in artifact_view.view_data().items():
        print(f"\n{category}")
        print(df.head())

    # Give any broker threads time to finish
    time.sleep(1)
