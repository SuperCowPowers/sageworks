"""SageWorks Dashboard: A SageWorks Web Application for viewing and managing SageWorks Artifacts"""

from dash import Dash, page_container, html, dcc
import dash_bootstrap_components as dbc
from sageworks.utils.plugin_manager import PluginManager


# Note: The 'app' and 'server' objects need to be at the top level since NGINX/uWSGI needs to
#       import this file and use the server object as an ^entry-point^ into the Dash Application Code

# Create our Dash Application
app = Dash(
    __name__,
    title="SageWorks Dashboard",
    external_stylesheets=[dbc.themes.DARKLY],
    use_pages=True,
)
server = app.server

# For Multi-Page Applications, we need to create a 'page container' to hold all the pages
app.layout = html.Div(
    [
        dcc.Store(id="aws-broker-data", storage_type="local"),
        page_container,
    ]
)

# Grab any plugin pages
pm = PluginManager()
plugin_pages = pm.get_pages()

# Setup each if the plugin pages (call layout and callbacks internally)
for name, page in plugin_pages.items():
    page.page_setup(app)


if __name__ == "__main__":
    """Run our web application in TEST mode"""
    # Note: This 'main' is purely for running/testing locally
    # app.run_server(host="0.0.0.0", port=8000, debug=True)
    app.run_server(host="0.0.0.0", port=8000)
