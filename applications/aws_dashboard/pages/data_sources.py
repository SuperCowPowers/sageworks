"""DataSources:  A SageWorks Web Interface to view, interact, and manage Data Sources"""
from dash import register_page
import dash
from dash_bootstrap_templates import load_figure_template

# SageWorks Imports
from sageworks.web_components import violin_plot, table, data_source_details
from sageworks.views.data_source_web_view import DataSourceWebView

# Local Imports
from pages.layout.data_sources_layout import data_sources_layout
import pages.callbacks.data_sources_callbacks as callbacks

register_page(__name__, path="/data_sources")


# Okay feels a bit weird but Dash pages just have a bunch of top level code (no classes/methods)

# Put the components into 'dark' mode
load_figure_template("darkly")

# Grab a view that gives us a summary of the DataSources in SageWorks
data_source_broker = DataSourceWebView()
data_source_rows = data_source_broker.data_sources_summary()

# Create a table to display the data sources
data_sources_table = table.create(
    "data_sources_table",
    data_source_rows,
    header_color="rgb(100, 60, 60)",
    row_select="single",
    markdown_columns=["Name"],
)

# Grab sample rows from the first data source
sample_rows = data_source_broker.data_source_sample(0)
data_source_sample_rows = table.create(
    "data_source_sample_rows",
    sample_rows,
    header_color="rgb(60, 60, 100)",
    max_height="200px",
)

# Data Source Details
details = data_source_broker.data_source_details(0)
data_details = data_source_details.create("data_source_details", details)

# Create a box plot of all the numeric columns in the sample rows
smart_sample_rows = data_source_broker.data_source_smart_sample(0)
violin = violin_plot.create("data_source_violin_plot", smart_sample_rows)

# Create our components
components = {
    "data_sources_table": data_sources_table,
    "data_source_details": data_details,
    "data_source_sample_rows": data_source_sample_rows,
    "violin_plot": violin,
}

# Setup our callbacks/connections
app = dash.get_app()

# Refresh our data timer
callbacks.refresh_data_timer(app)

# Periodic update to the data sources summary table
callbacks.update_data_sources_table(app, data_source_broker)

# Callbacks for when a data source is selected
callbacks.table_row_select(app, "data_sources_table")
callbacks.update_data_source_details(app, data_source_broker)
callbacks.update_data_source_sample_rows(app, data_source_broker)
callbacks.update_violin_plots(app, data_source_broker)

# Set up our layout (Dash looks for a var called layout)
layout = data_sources_layout(components)
