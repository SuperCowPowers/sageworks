"""A Singleton Plugin Manager Class: Manages the loading and retrieval of SageWorks plugins"""

import os
import atexit
import shutil
import tempfile
import logging
import importlib
from typing import Union, Dict, List, Any

# SageWorks Imports
from sageworks.utils.config_manager import ConfigManager
from sageworks.utils.s3_utils import copy_s3_files_to_local
from sageworks.views.view import View
from sageworks.web_components.plugin_interface import PluginInterface as WebPluginInterface
from sageworks.web_components.plugin_interface import PluginType as WebPluginType


class PluginManager:
    """A Singleton Plugin Manager Class: Manages the loading and retrieval of SageWorks plugins"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the class if it doesn't exist, else return the existing instance."""
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance.__initialized = False  # Gets initialized in __init__
        return cls._instance

    def __init__(self):
        """Initialize the PluginManager as a singleton."""
        if self.__initialized:
            return

        self.log = logging.getLogger("sageworks")
        self.config_plugin_dir = None
        self.loading_dir = False
        self.plugin_modified_time = None
        self.plugins: Dict[str, dict] = {"web_components": {}, "transforms": {}, "views": {}, "pages": {}}

        # Get the plugin directory from the config
        cm = ConfigManager()
        self.config_plugin_dir = cm.get_config("SAGEWORKS_PLUGINS")
        if not self.config_plugin_dir:
            self.log.warning("SAGEWORKS_PLUGINS not set. No plugins will be loaded.")
            return

        # Check if the config directory is local file or S3
        self.log.important(f"Loading plugins from {self.config_plugin_dir}...")
        if not self.config_plugin_dir.startswith("s3://"):
            self.loading_dir = self.config_plugin_dir

        # Load plugins from S3 (copy to a temporary directory, then load)
        else:
            self.loading_dir = tempfile.mkdtemp()
            copy_s3_files_to_local(self.config_plugin_dir, self.loading_dir)
            atexit.register(self._cleanup_temp_dir)

        # Load the plugins
        self.load_plugins()

        # Singleton is now initialized
        self.__initialized = True

    def load_plugins(self):
        """Loads plugins from our 'load_from' directory"""
        self.log.important(f"Loading plugins from {self.loading_dir}...")
        for plugin_type in self.plugins.keys():
            self._load_plugins(self.loading_dir, plugin_type)

        # Store the most recent modified time
        self.plugin_modified_time = self._most_recent_modified_time()

    def _load_plugins(self, base_dir: str, plugin_type: str):
        """Internal: Load plugins of a specific type from a subdirectory.

        Args:
            base_dir (str): Base directory of the plugins.
            plugin_type (str): Type of the plugin to load (e.g., web_components, pages, transforms).
        """
        type_dir = os.path.join(base_dir, plugin_type)
        if not os.path.isdir(type_dir):
            return

        for filename in os.listdir(type_dir):
            module = self._load_module(type_dir, filename)
            if module:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check if the attribute is a class and is defined in the module
                    if isinstance(attr, type) and attr.__module__ == module.__name__:
                        # For web components, check if the class is a subclass of WebPluginInterface
                        if plugin_type == "web_components" and issubclass(attr, WebPluginInterface):
                            self.log.important(f"Loading {plugin_type} plugin: {attr_name}")
                            self.plugins[plugin_type][attr_name] = attr

                        # For views, check if the class is a subclass of View
                        elif plugin_type == "views" and issubclass(attr, View):
                            self.log.important(f"Loading {plugin_type} plugin: {attr_name}")
                            self.plugins[plugin_type][attr_name] = attr

                        # For pages, check if the class has the required page plugin method (page_setup)
                        elif plugin_type == "pages":
                            if hasattr(attr, "page_setup"):
                                self.log.important(f"Loading page plugin: {attr_name}")
                                self.plugins[plugin_type][attr_name] = attr
                            else:
                                self.log.warning(
                                    f"Class {attr_name} in {filename} does not have all required page methods"
                                )

                        # Unexpected type
                        else:
                            self.log.warning(f"Class {attr_name} in {filename} invalid {plugin_type} plugin")

    @staticmethod
    def _load_module(dir_path: str, filename: str):
        """Internal: Load a module from a file"""
        if filename.endswith(".py") and not filename.startswith("_"):
            file_path = os.path.join(dir_path, filename)
            module_name = filename[:-3]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        return None

    def get_all_plugins(self) -> Dict[str, dict[Any]]:
        """
        Retrieve a dictionary of all plugins.

        Returns:
            Dict[str, dict]: A dictionary of all plugins.
                {'pages': {name: plugin, name2: plugin2,...
                 'views': {name: plugin, name2: plugin2,...},
        """
        return self.plugins

    def get_list_of_web_plugins(self, web_plugin_type: WebPluginType = None) -> List[Any]:
        """
        Retrieve a list of plugins of a specific type.

        Args:
            web_plugin_type (WebPluginType): The type of web plugin to retrieve (if applicable).

        Returns:
            List[Any]: A list of INSTANTIATED plugin classes of the requested type.
        """
        plugin_classes = [
            self.plugins["web_components"][x]
            for x in self.plugins["web_components"]
            if self.plugins["web_components"][x].plugin_type == web_plugin_type
        ]
        return [x() for x in plugin_classes]

    def get_web_plugin(self, plugin_name: str) -> WebPluginInterface:
        """
        Retrieve a specific web plugin by name

        Args:
            plugin_name (str): The name of the web plugin to retrieve

        Returns:
            WebPluginInterface: The INSTANTIATED web plugin class with the given name
        """
        web_plugin = self.plugins["web_components"].get(plugin_name)
        return web_plugin() if web_plugin else None

    def get_view(self, view_name: str) -> Union[View, None]:
        """
        Retrieve a view plugin with the given name.

        Args:
            view_name (str): The name of the view to retrieve (None if not found).

        Returns:
            View: An INSTANTIATED view class with the given name.
        """
        view = self.plugins["views"].get(view_name)
        return view() if view else None

    def get_pages(self) -> dict:
        """
        Retrieve a dict of plugins pages

        Returns:
           dict: A dict of INSTANTIATED plugin pages.
        """
        pages = self.plugins["pages"]
        return {name: page() for name, page in pages.items()}

    def _cleanup_temp_dir(self):
        """Cleans up the temporary directory created for S3 files."""
        if self.loading_dir and os.path.isdir(self.loading_dir):
            self.log.important(f"Cleaning up temporary directory: {self.loading_dir}")
            shutil.rmtree(self.loading_dir)
            self.loading_dir = None

    def plugins_modified(self) -> bool:
        """Check if the plugins have been modified since the last check

        Returns:
            bool: True if the plugins have been modified, else False
        """
        most_recent_time = self._most_recent_modified_time()
        if most_recent_time > self.plugin_modified_time:
            self.log.important("Plugins have been modified")
            self.plugin_modified_time = most_recent_time
            return True
        return False

    # Helper method to compute the most recent modified time
    def _most_recent_modified_time(self) -> float:
        """Internal: Compute the most recent modified time of a directory"""
        most_recent_time = 0
        for root, _, files in os.walk(self.loading_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_modified_time = os.path.getmtime(file_path)
                if file_modified_time > most_recent_time:
                    most_recent_time = file_modified_time
        return most_recent_time

    def __repr__(self) -> str:
        """String representation of the PluginManager state and contents

        Returns:
            str: String representation of the PluginManager state and contents
        """
        summary = "SAGEWORKS_PLUGINS: " + self.config_plugin_dir + "\n"
        summary += "Plugins:\n"
        for plugin_type, plugin_dict in self.plugins.items():
            for name, plugin in plugin_dict.items():
                summary += f"  {plugin_type}: {name}: {plugin}\n"
        return summary


if __name__ == "__main__":
    """Exercise the PluginManager class"""
    from pprint import pprint

    # Create the class, load plugins, and call various methods
    manager = PluginManager()

    # Get web components for the model view
    model_plugin = manager.get_list_of_web_plugins(WebPluginType.MODEL)

    # Get web components for the endpoint view
    endpoint_plugin = manager.get_list_of_web_plugins(WebPluginType.ENDPOINT)

    # Get view plugin
    my_view = manager.get_view("ModelPluginView")

    # Get plugin pages
    plugin_pages = manager.get_pages()

    # Get all the plugins
    pprint(manager.get_all_plugins())

    # Get a web plugin by name
    my_plugin = manager.get_web_plugin("CustomTurbo")
    print(my_plugin)

    # Test REPR
    print(manager)

    # Test Modified Time by modifying a plugin file
    cm = ConfigManager()
    plugin_path = cm.get_config("SAGEWORKS_PLUGINS") + "/web_components/custom_turbo.py"
    print(manager.plugins_modified())
    # Modify the plugin file modified time to now
    os.utime(plugin_path, None)
    print(manager.plugins_modified())

    # Test S3 Plugin Loading
    print("\n\n*** Testing S3 Plugin Loading ***\n\n")
    s3_path = "s3://sandbox-sageworks-artifacts/sageworks_plugins"
    cm = ConfigManager()
    cm.set_config("SAGEWORKS_PLUGINS", s3_path)

    # Since we're using a singleton, we need to create a new instance
    PluginManager._instance = None
    manager = PluginManager()

    # Get web components for the model view
    model_plugin = manager.get_list_of_web_plugins(WebPluginType.MODEL)

    # Get web components for the endpoint view
    endpoint_plugin = manager.get_list_of_web_plugins(WebPluginType.ENDPOINT)

    # Get view plugin
    my_view = manager.get_view("ModelPluginView")

    # Get plugin pages
    plugin_pages = manager.get_pages()

    # Get all the plugins
    pprint(manager.get_all_plugins())
