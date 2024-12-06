"""A confusion matrix plugin component"""

from dash import dcc, callback, Output, Input, State
import plotly.graph_objects as go
import plotly.io as pio


# SageWorks Imports
from sageworks.web_interface.components.plugin_interface import PluginInterface, PluginPage, PluginInputType
from sageworks.cached.cached_model import CachedModel
from sageworks.utils.theme_manager import ThemeManager


class ConfusionMatrix(PluginInterface):
    """Confusion Matrix Component"""

    auto_load_page = PluginPage.NONE
    plugin_input_type = PluginInputType.MODEL

    def __init__(self):
        """Initialize the ConfusionMatrix plugin class"""
        self.component_id = None
        self.current_highlight = None  # Store the currently highlighted cell

        # Initialize the Theme Manager
        self.theme_manager = ThemeManager()

        # Call the parent class constructor
        super().__init__()

    def create_component(self, component_id: str) -> dcc.Graph:
        """Create a Confusion Matrix Component without any data.

        Args:
            component_id (str): The ID of the web component
        Returns:
            dcc.Graph: The Confusion Matrix Component
        """
        self.component_id = component_id
        self.container = dcc.Graph(
            id=component_id,
            figure=self.display_text("Waiting for Data..."),
            config={"scrollZoom": False, "doubleClick": "reset"},
        )

        # Fill in plugin properties
        self.properties = [(self.component_id, "figure")]
        self.signals = [(self.component_id, "clickData")]

        return self.container

    def update_properties(self, model: CachedModel, **kwargs) -> list:
        """
        Create a Confusion Matrix Figure for the numeric columns in the dataframe.

        Args:
            model (CachedModel): Sageworks instantiated CachedModel object
            **kwargs:
                - inference_run (str): Inference capture UUID
        Returns:
            list: A list containing the updated Plotly figure.
        """
        # Retrieve the confusion matrix data
        inference_run = kwargs.get("inference_run", "auto_inference")
        df = model.confusion_matrix(inference_run)
        if df is None:
            return self.display_text("No Data")

        # Use Plotly's default theme-friendly colorscale
        # from plotly.colors import sequential
        # color_scale = sequential.Plasma

        # The confusion matrix is displayed in reverse order (flip the dataframe for correct orientation)
        df = df.iloc[::-1]

        # Add labels to the confusion matrix, including the index for highlighting
        x_labels = [f"{c}:{i}" for i, c in enumerate(df.columns)]
        y_labels = [f"{c}:{i}" for i, c in enumerate(df.index)]

        # Create the heatmap figure
        fig = go.Figure(
            data=go.Heatmap(
                z=df,
                x=x_labels,
                y=y_labels,
                xgap=2,  # Add space between cells
                ygap=2,
                colorscale=self.theme_manager.colorscale(),  # Use the current theme's colorscale
            )
        )

        # Apply theme-based layout updates
        fig.update_layout(
            template=pio.templates.default,  # Use the current theme
            margin={"t": 10, "b": 10, "r": 10, "l": 10, "pad": 10},  # Tight margins
            height=400,  # Fixed height for consistent layout
            xaxis_title="Predicted",  # Add meaningful axis labels
            yaxis_title="Actual",
        )

        # Configure x-axis with dynamic theming
        fig.update_xaxes(
            tickvals=x_labels,  # Position ticks for each label
            ticktext=df.columns,  # Display readable column names
            tickangle=30,  # Rotate labels for better readability
            tickfont_size=14,  # Font size for tick labels
            automargin=True,  # Automatically manage margins
            title_standoff=20,  # Add space between axis title and labels
            title_font={"size": 18},  # Use theme-defined colors
        )

        # Configure y-axis with dynamic theming
        fig.update_yaxes(
            tickvals=y_labels,  # Position ticks for each label
            ticktext=df.index,  # Display readable row names
            tickfont_size=14,  # Font size for tick labels
            automargin=True,  # Automatically manage margins
            title_standoff=20,  # Add space between axis title and labels
            title_font={"size": 18},  # Use theme-defined colors
        )

        # Add annotations for each cell in the confusion matrix
        for i, row in enumerate(df.index):
            for j, col in enumerate(df.columns):
                value = df.loc[row, col]
                text_value = f"{value:.2f}" if isinstance(value, float) else str(value)
                fig.add_annotation(
                    x=j,  # Cell column position
                    y=i,  # Cell row position
                    text=text_value,  # Display the value in the cell
                    showarrow=False,  # No arrows, place directly in the cell
                    font_size=16,  # Font size for cell values
                )

        # Return the updated figure wrapped in a list
        return [fig]

    def register_internal_callbacks(self):
        """Register internal callbacks for the plugin."""

        @callback(
            Output(self.component_id, "figure", allow_duplicate=True),
            Input(self.component_id, "clickData"),
            State(self.component_id, "figure"),
            prevent_initial_call=True,
        )
        def highlight_cm_square(click_data, current_figure):
            """Highlight the selected confusion matrix square."""
            if not click_data or "points" not in click_data:
                return current_figure  # No click data, return the current figure

            # Extract clicked point
            point = click_data["points"][0]
            x_index = point["x"]
            y_index = point["y"]

            # Parse the index from labels (e.g., "label:1")
            x_label, x_idx = x_index.split(":")
            y_label, y_idx = y_index.split(":")
            x_idx, y_idx = int(x_idx), int(y_idx)

            # Create a new rectangle for highlighting
            delta = 0.5
            highlight_shape = {
                "type": "rect",
                "x0": x_idx - delta,
                "x1": x_idx + delta,
                "y0": y_idx - delta,
                "y1": y_idx + delta,
                "line": {"color": "grey", "width": 2},
                "layer": "above",
            }

            # Add the highlight
            current_figure["layout"]["shapes"] = [highlight_shape]

            return current_figure


if __name__ == "__main__":
    """Run the Unit Test for the Plugin."""
    from sageworks.web_interface.components.plugin_unit_test import PluginUnitTest

    # Run the Unit Test on the Plugin
    model = CachedModel("wine-classification")
    PluginUnitTest(ConfusionMatrix, input_data=model, theme="dark").run()
