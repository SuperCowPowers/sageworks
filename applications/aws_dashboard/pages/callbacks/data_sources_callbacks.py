"""FeatureSets Callbacks: Callback within the DataSources Web User Interface"""
from datetime import datetime
import dash
from dash import Dash
from dash.dependencies import Input, Output

# SageWorks Imports
from sageworks.views.data_source_view import DataSourceView


def update_last_updated(app: Dash):
    @app.callback(Output("last-updated-data-sources", "children"), Input("data-sources-updater", "n_intervals"))
    def time_updated(n):
        return datetime.now().strftime("Last Updated: %Y-%m-%d %H:%M:%S")


def update_data_sources_summary(app: Dash, data_source_view: DataSourceView):
    @app.callback(Output("data_sources_summary", "data"), Input("data-sources-updater", "n_intervals"))
    def data_sources_update(n):
        print("Calling DataSources Summary Refresh...")
        data_source_view.refresh()
        data_sources = data_source_view.data_sources_summary()
        return data_sources.to_dict("records")


# Highlights the selected row in the table
def table_row_select(app: Dash, table_name: str):
    @app.callback(
        Output(table_name, "style_data_conditional"),
        Input(table_name, "derived_viewport_selected_row_ids"),
    )
    def style_selected_rows(selected_rows):
        print(f"Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        foo = [
            {
                "if": {"filter_query": "{{id}} ={}".format(i)},
                "backgroundColor": "rgb(80, 80, 80)",
            }
            for i in selected_rows
        ]
        return foo


def update_data_source_sample_rows(app: Dash, data_source_view: DataSourceView):
    @app.callback(Output("data_source_sample_rows", "data"), Input("data-sources-updater", "n_intervals"))
    def data_sources_update(n):
        print("Calling DataSource Sample Rows Refresh...")
        data_source_view.refresh()
        data_sources = data_source_view.data_sources_summary()
        return data_sources.to_dict("records")