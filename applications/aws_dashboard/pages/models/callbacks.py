"""Callbacks for the Model Subpage Web User Interface"""

from dash import Dash, no_update
from dash.dependencies import Input, Output, State

# SageWorks Imports
from sageworks.views.model_web_view import ModelWebView
from sageworks.web_components import (
    table,
    model_details_markdown,
    model_metrics_markdown,
    model_plot,
)
from sageworks.utils.pandas_utils import deserialize_aws_broker_data
from sageworks.api.model import Model


def update_models_table(app: Dash):
    @app.callback(
        [Output("models_table", "columns"), Output("models_table", "data")],
        Input("aws-broker-data", "data"),
    )
    def models_update(serialized_aws_broker_data):
        """Return the table data for the Models Table"""
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        models = aws_broker_data["MODELS"]
        models["id"] = range(len(models))
        column_setup_list = table.Table().column_setup(models, markdown_columns=["Model Group"])
        return [column_setup_list, models.to_dict("records")]


# Highlights the selected row in the table
def table_row_select(app: Dash, table_name: str):
    @app.callback(
        Output(table_name, "style_data_conditional"),
        Input(table_name, "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def style_selected_rows(selected_rows):
        if not selected_rows or selected_rows[0] is None:
            return no_update
        row_style = [
            {
                "if": {"filter_query": "{{id}}={}".format(i)},
                "backgroundColor": "rgb(80, 80, 80)",
            }
            for i in selected_rows
        ]
        # Style for symbols
        symbol_style = {"if": {"column_id": "Health"}, "fontSize": 16, "textAlign": "left"}

        # Append the symbol style to the row style
        row_style.append(symbol_style)
        return row_style


# Updates the model details when a model row is selected
def update_model_detail_component(app: Dash):
    @app.callback(
        [Output("model_details_header", "children"), Output("model_details", "children")],
        Input("models_table", "derived_viewport_selected_row_ids"),
        State("models_table", "data"),
        prevent_initial_call=True,
    )
    def generate_model_details_figure(selected_rows, table_data):
        # Check for no selected rows
        if not selected_rows or selected_rows[0] is None:
            return no_update

        # Get the selected row data and grab the uuid
        selected_row_data = table_data[selected_rows[0]]
        model_uuid = selected_row_data["uuid"]
        m = Model(model_uuid)

        # Set the Header Text
        header = f"Model: {model_uuid}"

        # Model Details Markdown component
        model_details_fig = model_details_markdown.ModelDetailsMarkdown().generate_markdown(m)

        # Return the details/markdown for these data details
        return [header, model_details_fig]


# Updates Inference Run Selector Component
def update_inference_dropdown(app: Dash):
    @app.callback(
        [Output("inference_dropdown", "options"), Output("inference_dropdown", "value")],
        Input("models_table", "derived_viewport_selected_row_ids"),
        State("models_table", "data"),
        prevent_initial_call=True,
    )
    def generate_inference_dropdown_figure(selected_rows, table_data):
        # Check for no selected rows
        if not selected_rows or selected_rows[0] is None:
            return no_update

        # Get the selected row data and grab the uuid
        selected_row_data = table_data[selected_rows[0]]
        model_uuid = selected_row_data["uuid"]
        m = Model(model_uuid)

        # Inference runs
        inference_runs = m.list_inference_runs()

        # Check if there are any inference runs to select
        if not inference_runs:
            return [], None

        # Set "training_holdout" as the default, if that doesn't exist, set the first
        default_inference_run = "training_holdout" if "training_holdout" in inference_runs else inference_runs[0]

        # Return the options for the dropdown and the selected value
        return inference_runs, default_inference_run


# Updates the model metrics when a model row is selected
def update_model_metrics_component(app: Dash):
    @app.callback(
        Output("model_metrics", "children"),
        [Input("models_table", "derived_viewport_selected_row_ids"), Input("inference_dropdown", "value")],
        State("models_table", "data"),
        prevent_initial_call=True,
    )
    def generate_model_metrics_figure(selected_rows, inference_run, table_data):
        # Check for no selected rows
        if not selected_rows or selected_rows[0] is None:
            return no_update

        # Get the selected row data and grab the uuid
        selected_row_data = table_data[selected_rows[0]]
        model_uuid = selected_row_data["uuid"]
        m = Model(model_uuid)

        # Model Details Markdown component
        model_metrics_fig = model_metrics_markdown.ModelMetricsMarkdown().generate_markdown(m, inference_run)

        # Return the details/markdown for these data details
        return model_metrics_fig


# Updates the model plot when a model row is selected
def update_model_plot_component(app: Dash):
    @app.callback(
        Output("model_plot", "figure"),
        [Input("models_table", "derived_viewport_selected_row_ids"), Input("inference_dropdown", "value")],
        State("models_table", "data"),
        prevent_initial_call=True,
    )
    def generate_model_plot_figure(selected_rows, inference_run, table_data):
        # Check for no selected rows
        if not selected_rows or selected_rows[0] is None:
            return no_update

        # Get the selected row data and grab the uuid
        selected_row_data = table_data[selected_rows[0]]
        model_uuid = selected_row_data["uuid"]
        m = Model(model_uuid)

        # Model Details Markdown component
        model_plot_fig = model_plot.ModelPlot().generate_figure(m, inference_run)

        # Return the details/markdown for these data details
        return model_plot_fig


# Updates the plugin component when a model row is selected
def update_plugin(app: Dash, plugin, model_web_view: ModelWebView):
    @app.callback(
        Output(plugin.component_id(), "figure"),
        Input("models_table", "derived_viewport_selected_row_ids"),
        State("models_table", "data"),
        prevent_initial_call=True,
    )
    def update_plugin_figure(selected_rows, table_data):
        # Check for no selected rows
        if not selected_rows or selected_rows[0] is None:
            return no_update

        # Get the selected row data and grab the uuid
        selected_row_data = table_data[selected_rows[0]]
        model_uuid = selected_row_data["uuid"]

        # Instantiate the Model and send it to the plugin
        model = Model(model_uuid)
        return plugin.generate_figure(model)
