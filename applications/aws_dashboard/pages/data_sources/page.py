"""DataSources:  A SageWorks Web Interface to view, interact, and manage Data Sources"""

from dash import register_page

# SageWorks Imports
from sageworks.web_interface.components import data_details_markdown, violin_plots, correlation_matrix
from sageworks.web_interface.components.plugins.ag_table import AGTable
from sageworks.web_interface.page_views.data_sources_page_view import DataSourcesPageView

# Local Imports
from .layout import data_sources_layout
from . import callbacks

register_page(
    __name__,
    path="/data_sources",
    name="SageWorks - Data Sources",
)


# Create a table to display the Data Sources
data_sources_table = AGTable()
data_sources_component = data_sources_table.create_component(
    "data_sources_table",
    header_color="rgb(120, 70, 70)",
    max_height=270,
)

# Create a table that sample rows from the currently selected data source
samples_table = AGTable()
samples_component = samples_table.create_component(
    "data_source_sample_rows",
    header_color="rgb(70, 70, 110)",
    max_height=250,
)

# Data Source Details Markdown PANEL
data_details = data_details_markdown.DataDetailsMarkdown().create_component("data_source_details")

# Create a violin plot of all the numeric columns in the Data Source
violin = violin_plots.ViolinPlots().create_component("data_source_violin_plot")

# Create a correlation matrix of all the numeric columns in the Data Source
corr_matrix = correlation_matrix.CorrelationMatrix().create_component("data_source_correlation_matrix")

# Create our components
components = {
    "data_sources_table": data_sources_component,
    "data_source_sample_rows": samples_component,
    "data_source_details": data_details,
    "violin_plot": violin,
    "correlation_matrix": corr_matrix,
}

# Set up our layout (Dash looks for a var called layout)
layout = data_sources_layout(**components)

# Grab a view that gives us a summary of the DataSources in SageWorks
data_source_view = DataSourcesPageView()

# Callback for anything we want to happen on page load
callbacks.on_page_load()

# Periodic update to the data sources summary table
callbacks.data_sources_refresh(data_source_view, data_sources_table)

# Callbacks for when a data source is selected
callbacks.update_data_source_details(data_source_view)
callbacks.update_data_source_sample_rows(data_source_view, samples_table)

# Callbacks for selections
callbacks.violin_plot_selection()
callbacks.reorder_sample_rows()
callbacks.correlation_matrix_selection()
