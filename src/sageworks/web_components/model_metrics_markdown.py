"""A Markdown Component for model metrics"""

from dash import dcc

# SageWorks Imports
from sageworks.api import Model
from sageworks.web_components.component_interface import ComponentInterface


class ModelMetricsMarkdown(ComponentInterface):
    """Model Markdown Component"""

    def create_component(self, component_id: str) -> dcc.Markdown:
        """Create a Markdown Component without any data.
        Args:
            component_id (str): The ID of the web component
        Returns:
            dcc.Markdown: The Dash Markdown Component
        """
        waiting_markdown = "*Waiting for data...*"
        return dcc.Markdown(id=component_id, children=waiting_markdown, dangerously_allow_html=False)

    def generate_markdown(self, model: Model, inference_run: str) -> str:
        """Create the Markdown for the details/information about the DataSource or the FeatureSet
        Args:
            model (Model): Sageworks Model object
            inference_run (str): Valid capture_uuid
        Returns:
            str: A Markdown string
        """

        # Model Metrics
        markdown = "### Model Metrics  \n"
        meta_df = model.inference_metadata(inference_run)
        if meta_df is None:
            test_data = "Inference Metadata Not Found"
            test_data_hash = " N/A "
            test_rows = " - "
            description = " - "
        else:
            inference_meta = meta_df.to_dict(orient="records")[0]
            test_data = inference_meta.get("name", " - ")
            test_data_hash = inference_meta.get("data_hash", " - ")
            test_rows = inference_meta.get("num_rows", " - ")
            description = inference_meta.get("description", " - ")

        # Add the markdown for the model test metrics
        markdown += f"**Test Data:** {test_data}  \n"
        markdown += f"**Data Hash:** {test_data_hash}  \n"
        markdown += f"**Test Rows:** {test_rows}  \n"
        markdown += f"**Description:** {description}  \n"

        # Grab the Metrics from the model details
        metrics = model.performance_metrics(capture_uuid=inference_run)
        if metrics is None:
            markdown += "  \nNo Data  \n"
        else:
            markdown += "  \n"
            metrics = metrics.round(3)
            markdown += metrics.to_markdown(index=False)

        return markdown


if __name__ == "__main__":
    # This class takes in model metrics and generates a Markdown Component
    import dash
    from dash import dcc, html
    import dash_bootstrap_components as dbc
    from sageworks.api import Model

    # Create the class and get the AWS FeatureSet details
    m = Model("wine-classification")
    inference_run = "model_training"

    # Instantiate the DataDetailsMarkdown class
    ddm = ModelMetricsMarkdown()
    component = ddm.create_component("model_metrics_markdown")

    # Generate the markdown
    markdown = ddm.generate_markdown(m, inference_run)

    print(markdown)

    # Show the Markdown in the Web Browser
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY],
    )

    app.layout = html.Div([component])
    component.children = markdown

    if __name__ == "__main__":
        app.run_server(debug=True)
