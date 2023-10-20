"""A confusion matrix plugin component"""
from dash import dcc
import plotly.graph_objects as go


# SageWorks Imports
from sageworks.web_components.component_interface import ComponentInterface


class ConfusionMatrix(ComponentInterface):
    """Confusion Matrix Component"""

    def create_component(self, component_id: str) -> dcc.Graph:
        """Create a Confusion Matrix Component without any data.
        Args:
            component_id (str): The ID of the web component
        Returns:
            dcc.Graph: The Confusion Matrix Component
        """
        return dcc.Graph(id=component_id, figure=self.message_figure("Waiting for Data..."))

    def generate_component_figure(self, model_details: dict) -> go.Figure:
        """Create a Confusion Matrix Figure for the numeric columns in the dataframe.
        Args:
            model_details (dict): The model details dictionary
        Returns:
            plotly.graph_objs.Figure: A Figure object containing the confusion matrix.
        """

        # Grab the confusion matrix from the model details
        df = model_details.get("confusion_matrix")
        if df is None:
            return self.message_figure("No Data")

        # A nice color scale for the confusion matrix
        color_scale = [
            [0, "rgb(64,64,160)"],
            [0.35, "rgb(48, 140, 140)"],
            [0.65, "rgb(140, 140, 48)"],
            [1.0, "rgb(160, 64, 64)"],
        ]

        # Okay so the heatmap has inverse y-axis ordering so we need to flip the dataframe
        df = df.iloc[::-1]

        # Okay so there are numerous issues with getting back the index of the clicked on point
        # so we're going to store the indexes of the columns (this is SO stupid)
        x_labels = [f"{c}:{i}" for i, c in enumerate(df.columns)]
        y_labels = [f"{c}:{i}" for i, c in enumerate(df.index)]

        # Create the heatmap plot with custom settings
        fig = go.Figure(
            data=go.Heatmap(
                z=df,
                x=x_labels,
                y=y_labels,
                name="",
                colorscale=color_scale,
                zmin=0,
            )
        )
        fig.update_layout(margin={"t": 10, "b": 10, "r": 10, "l": 10, "pad": 10}, height=400)

        # Now remap the x and y axis labels (so they don't show the index)
        fig.update_xaxes(tickvals=x_labels, ticktext=df.columns, tickangle=30, tickfont_size=14)
        fig.update_yaxes(tickvals=y_labels, ticktext=df.index, tickfont_size=14)

        # Now we're going to customize the annotations
        for i, row in enumerate(df.index):
            for j, col in enumerate(df.columns):
                value = df.loc[row, col]

                # For floats, we want to show 2 decimal places
                text_value = f"{value:.2f}" if isinstance(value, float) else str(value)
                fig.add_annotation(x=j, y=i, text=text_value, showarrow=False, font_size=14)

        return fig


if __name__ == "__main__":
    # This class takes in model details and generates a Confusion Matrix
    from sageworks.artifacts.models.model import Model

    # m = Model("abalone-regression")
    m = Model("wine-classification")
    model_details = m.details()

    # Instantiate the ConfusionMatrix class
    cm = ConfusionMatrix()

    # Generate the figure
    fig = cm.generate_component_figure(model_details)

    # Apply dark theme
    fig.update_layout(template="plotly_dark")

    # Show the figure
    fig.show()
