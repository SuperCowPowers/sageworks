"""Tests for graph_plot web component"""

# SageWorks Imports
from sageworks.core.artifacts.graph_core import GraphCore
from sageworks.web_components.plugins.graph_plot import GraphPlot


def test_graph_plot():
    """Test the GraphPlot class"""

    # Instantiate a Graph
    graph = GraphCore("karate_club")

    # Instantiate the GraphPlot class
    graph_plot = GraphPlot()

    # Generate the figure
    [figure] = graph_plot.update_properties(graph)
    figure.show()


if __name__ == "__main__":
    # Run the tests
    test_graph_plot()
