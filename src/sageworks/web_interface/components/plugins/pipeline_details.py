"""A Markdown Component for details/information about Pipelines"""

import logging

# Dash Imports
from dash import html, dcc

# SageWorks Imports
from sageworks.api.pipeline import Pipeline
from sageworks.utils.markdown_utils import health_tag_markdown
from sageworks.web_interface.components.plugin_interface import PluginInterface, PluginPage, PluginInputType

# Get the SageWorks logger
log = logging.getLogger("sageworks")


class PipelineDetails(PluginInterface):
    """Pipeline Details Markdown Component"""

    """Initialize this Plugin Component Class with required attributes"""
    auto_load_page = PluginPage.NONE
    plugin_input_type = PluginInputType.PIPELINE

    def __init__(self):
        """Initialize the PipelineDetails plugin class"""
        self.component_id = None
        self.current_pipeline = None

        # Call the parent class constructor
        super().__init__()

    def create_component(self, component_id: str) -> html.Div:
        """Create a Markdown Component without any data.
        Args:
            component_id (str): The ID of the web component
        Returns:
            html.Div: A Container of Components for the Model Details
        """
        self.component_id = component_id
        container = html.Div(
            id=self.component_id,
            children=[
                html.H3(id=f"{self.component_id}-header", children="Pipeline: Loading..."),
                dcc.Markdown(id=f"{self.component_id}-details"),
            ],
        )

        # Fill in plugin properties
        self.properties = [
            (f"{self.component_id}-header", "children"),
            (f"{self.component_id}-details", "children"),
        ]

        # Return the container
        return container

    def update_properties(self, pipeline: Pipeline, **kwargs) -> list:
        """Update the properties for the plugin.

        Args:
            pipeline (Pipeline): An instantiated Pipeline object
            **kwargs: Additional keyword arguments (unused)

        Returns:
            list: A list of the updated property values for the plugin
        """
        log.important(f"Updating Plugin with Pipeline: {pipeline.uuid} and kwargs: {kwargs}")

        # Update the header and the details
        self.current_pipeline = pipeline
        header = f"{self.current_pipeline.uuid}"
        details = self.pipeline_details()

        # Return the updated property values for the plugin
        return [header, details]

    def pipeline_details(self):
        """Construct the markdown string for the pipeline details

        Returns:
            str: A markdown string
        """

        # Construct the markdown string
        details = self.current_pipeline.details()
        markdown = ""
        for key, value in details.items():

            # If the value is a list, convert it to a comma-separated string
            if isinstance(value, list):
                value = ", ".join(value)

            # If the value is a dictionary, get the name
            if isinstance(value, dict):
                value = value.get("name", "Unknown")

            # Add to markdown string
            markdown += f"**{key}:** {value}  \n"

        return markdown


if __name__ == "__main__":
    # This class takes in pipeline details and generates a details Markdown component
    from sageworks.web_interface.components.plugin_unit_test import PluginUnitTest

    # Run the Unit Test on the Plugin
    PluginUnitTest(PipelineDetails).run()
