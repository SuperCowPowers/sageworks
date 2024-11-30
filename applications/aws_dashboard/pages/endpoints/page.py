"""Endpoints:  A SageWorks Web Interface to view and interact with Endpoints"""

from dash import register_page

# Local Imports
from .layout import endpoints_layout
from . import callbacks

# SageWorks Imports
from sageworks.web_interface.components import table, endpoint_metric_plots
from sageworks.web_interface.components.plugins import endpoint_details
from sageworks.web_interface.components.plugin_interface import PluginPage
from sageworks.web_interface.page_views.endpoints_page_view import EndpointsPageView
from sageworks.utils.plugin_manager import PluginManager

# Register this page with Dash
register_page(
    __name__,
    path="/endpoints",
    name="SageWorks - Endpoints",
)


# Create a table to display the endpoints
endpoints_table = table.Table().create_component(
    "endpoints_table", header_color="rgb(100, 60, 100)", row_select="single", max_height=270
)

# Create a Markdown component to display the endpoint details
endpoint_details = endpoint_details.EndpointDetails()
endpoint_details_component = endpoint_details.create_component("endpoint_details")

# Create a component to display the endpoint metrics
endpoint_metrics = endpoint_metric_plots.EndpointMetricPlots().create_component("endpoint_metrics")

# Capture our components in a dictionary to send off to the layout
components = {
    "endpoints_table": endpoints_table,
    "endpoint_details": endpoint_details_component,
    "endpoint_metrics": endpoint_metrics,
}

# Load any web components plugins of type 'endpoint'
pm = PluginManager()
plugins = pm.get_list_of_web_plugins(plugin_page=PluginPage.ENDPOINT)

# Our endpoint details is a plugin, so we need to add it to the list
plugins.append(endpoint_details)

# Add the plugins to the components dictionary
for plugin in plugins:
    component_id = plugin.generate_component_id()
    components[component_id] = plugin.create_component(component_id)

# Set up our layout (Dash looks for a var called layout)
layout = endpoints_layout(**components)

# Grab a view that gives us a summary of the Endpoints in SageWorks
endpoints_view = EndpointsPageView()

# Setup our callbacks/connections
callbacks.update_endpoints_table(endpoints_view)

# Callback for the endpoints table
callbacks.table_row_select("endpoints_table")
callbacks.update_endpoint_metrics(endpoints_view)

# For all the plugins we have we'll call their update_properties method
if plugins:
    callbacks.setup_plugin_callbacks(plugins)
