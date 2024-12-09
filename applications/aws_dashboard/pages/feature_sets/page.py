"""DataSources:  A SageWorks Web Interface to view, interact, and manage Data Sources"""

from dash import register_page

# SageWorks Imports
from sageworks.web_interface.components import data_details_markdown, violin_plots, correlation_matrix
from sageworks.web_interface.components.plugins.ag_table import AGTable
from sageworks.web_interface.page_views.feature_sets_page_view import FeatureSetsPageView

# Local Imports
from .layout import feature_sets_layout
from . import callbacks

register_page(__name__, path="/feature_sets", name="SageWorks - Feature Sets")

# Create a table to display the Feature Sets
feature_sets_table = AGTable()
feature_sets_component = feature_sets_table.create_component(
    "feature_sets_table", header_color="rgb(60, 100, 60)", max_height=270
)

# Grab smart_sample rows from the first Feature Set
samples_table = AGTable()
samples_component = samples_table.create_component(
    "feature_set_sample_rows",
    header_color="rgb(70, 70, 110)",
    max_height=250,
)

# Feature Set Details
feature_details = data_details_markdown.DataDetailsMarkdown().create_component("feature_set_details")

# Create a violin plot of all the numeric columns in the Feature Set
violin = violin_plots.ViolinPlots().create_component("feature_set_violin_plot")

# Create a correlation matrix component
corr_matrix = correlation_matrix.CorrelationMatrix().create_component("feature_set_correlation_matrix")


# Create our components
components = {
    "feature_sets_table": feature_sets_component,
    "feature_set_sample_rows": samples_component,
    "feature_set_details": feature_details,
    "violin_plot": violin,
    "correlation_matrix": corr_matrix,
}

# Set up our layout (Dash looks for a var called layout)
layout = feature_sets_layout(**components)

# Grab a view that gives us a summary of the FeatureSets in SageWorks
feature_set_view = FeatureSetsPageView()

# Periodic update to the feature sets summary table
callbacks.feature_sets_refresh(feature_set_view, feature_sets_table)

# Callbacks for when a feature set is selected
callbacks.update_feature_set_details(feature_set_view)
callbacks.update_feature_set_sample_rows(feature_set_view, samples_table)

# Callbacks for selections
callbacks.violin_plot_selection()
callbacks.reorder_sample_rows()
callbacks.correlation_matrix_selection()
