"""A Regression Plot component"""

from dash import dcc
import plotly.graph_objects as go
import plotly.express as px

# SageWorks Imports
from sageworks.web_interface.components.component_interface import ComponentInterface
from sageworks.api import Model
from sageworks.utils.theme_manager import ThemeManager


# This class is basically a specialized version of a Plotly Scatter Plot
# For heatmaps see (https://plotly.com/python/line-and-scatter/)
class RegressionPlot(ComponentInterface):
    """Regression Plot Component"""

    def __init__(self):
        """Initialize the Regression Plot Class"""

        # Initialize the Theme Manager
        self.theme_manager = ThemeManager()

        # Call the parent class constructor
        super().__init__()

    def create_component(self, component_id: str) -> dcc.Graph:
        # Initialize an empty scatter plot figure
        return dcc.Graph(id=component_id, figure=self.display_text("Waiting for Data..."))

    def update_properties(self, model: Model, inference_run: str) -> go.Figure:
        # Get predictions for specific inference
        df = model.get_inference_predictions(inference_run)

        if df is None:
            return self.display_text("No Data")

        # Get the name of the actual field value column
        actual_col = [col for col in df.columns if col != "prediction"][0]

        # Calculate the distance from the diagonal for each point
        df["prediction_error"] = abs(df["prediction"] - df[actual_col])

        # Create the scatter plot with bigger dots
        fig = px.scatter(
            df,
            x=actual_col,
            y="prediction",
            size="prediction_error",
            size_max=20,
            color="prediction_error",
            color_continuous_scale=self.theme_manager.colorscale(),
        )

        # Customize axis labels
        fig.update_layout(
            xaxis_title=dict(text=actual_col, font=dict(size=18)),
            yaxis_title=dict(text="Prediction", font=dict(size=18)),
        )

        # Just fine-tuning the dots on the scatter plot
        fig.update_traces(
            marker=dict(size=14, line=dict(width=1, color="Black")),
            selector=dict(mode="markers"),
        )

        # Add a diagonal line for reference
        min_val = min(df[actual_col].min(), df["prediction"].min())
        max_val = max(df[actual_col].max(), df["prediction"].max())
        fig.add_shape(
            type="line",
            line=dict(width=5, color="rgba(1.0, 1.0, 1.0, 0.5)"),
            x0=min_val,
            x1=max_val,
            y0=min_val,
            y1=max_val,
        )

        # Just some fine-tuning of the plot
        fig.update_layout(margin={"t": 10, "b": 10, "r": 10, "l": 10, "pad": 10}, height=400)

        return fig


if __name__ == "__main__":
    # This class takes in model details and generates a Confusion Matrix
    from sageworks.api import Model

    tm = ThemeManager()
    tm.set_theme("dark")

    m = Model("abalone-regression")
    my_inference_run = "model_training"

    # Instantiate the RegressionPlot class
    reg_plot = RegressionPlot()

    # Generate the figure
    fig = reg_plot.update_properties(m, my_inference_run)

    # Apply dark theme
    fig.update_layout()

    # Show the figure
    fig.show()
