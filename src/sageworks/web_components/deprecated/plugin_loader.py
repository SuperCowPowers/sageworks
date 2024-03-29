import os
import importlib.util
from typing import List
import logging
import inspect

# SageWorks imports
from sageworks.web_components.plugin_interface import PluginInterface, PluginPage


# SageWorks Logger
log = logging.getLogger("sageworks")


def load_plugins_from_dir(directory: str, plugin_page: PluginPage) -> List[PluginInterface]:
    """Load all the plugins from the given directory.
    Args:
        directory (str): The directory to load the plugins from.
        plugin_page (PluginPage): The type of plugin to load.
    Returns:
        List[PluginInterface]: A list of plugins that were loaded.
    """

    if not os.path.isdir(directory):
        log.warning(f"Directory {directory} does not exist. No plugins loaded.")
        return []

    plugins = []
    for filename in os.listdir(directory):
        if filename.endswith(".py"):
            file_path = os.path.join(directory, filename)
            spec = importlib.util.spec_from_file_location(filename, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for _, attribute in inspect.getmembers(module, inspect.isclass):
                if attribute.__module__ == module.__name__:
                    if issubclass(attribute, PluginInterface) and attribute is not PluginInterface:
                        try:
                            instance = attribute()
                            if instance.plugin_page == plugin_page:
                                plugins.append(instance)
                        except TypeError as e:
                            log.error(f"Error initializing plugin from {filename}: {e}")
                    else:
                        log.warning(f"Class {attribute.__name__} in {filename} invalid PluginInterface subclass")

    return plugins


if __name__ == "__main__":
    # Example of loading plugins from a directory
    from sageworks.utils.config_manager import ConfigManager

    # Get the plugin directory from the environment variable
    plugin_dir = ConfigManager().get_config("SAGEWORKS_PLUGINS")

    # Loop through the various plugin types and load the plugins
    plugin_pages = [PluginPage.DATA_SOURCE, PluginPage.FEATURE_SET, PluginPage.MODEL, PluginPage.ENDPOINT]
    for plugin_page in plugin_pages:
        plugins = load_plugins_from_dir(plugin_dir, plugin_page)
        for plugin in plugins:
            log.info(f"Loaded {plugin_page} plugin: {plugin.__class__.__name__}")
