import json
import os
import platform
import logging
import importlib.resources as resources
from typing import Any, Dict

# Set up the logger
import sageworks  # noqa: F401 (we need to import this to set up the logger)

log = logging.getLogger("sageworks")


class ConfigManager:
    def __init__(self):
        """Initialize the ConfigManager."""
        self.site_config_path = None
        self.needs_bootstrap = False
        self.config = self._load_config()

    def get_config(self, key: str) -> Any:
        """Get a configuration value by key.

        Args:
            key (str): The configuration key to retrieve.

        Returns:
            Any: The value of the configuration key.
        """
        # Special logic for SAGEWORKS_PLUGINS
        if key == "SAGEWORKS_PLUGINS":
            plugin_dir = self.config.get(key, None)
            if plugin_dir in ["package", "", None]:
                return os.path.join(os.path.dirname(__file__), "../../../applications/aws_dashboard/sageworks_plugins")
            else:
                return self.config.get(key, None)

        # Normal logic
        return self.config.get(key, None)

    def create_site_config(self):
        """Create a site configuration file from the default configuration."""
        site_config_updates = {}

        # Grab the bootstrap config
        bootstrap_config = self._load_bootstrap_config()

        # Prompt for each configuration value
        for key, value in bootstrap_config.items():
            if value == "change_me":
                value = input(f"Enter a value for {key}: ")
                site_config_updates[key] = value
            elif value == "change_me_optional":
                value = input(f"Enter a value for {key} (optional): ")
                if value in ["", None]:
                    site_config_updates[key] = None

        # Update default config with provided values
        site_config = {**bootstrap_config, **site_config_updates}

        # Determine platform-specific path (e.g., ~/.sageworks/config.json)
        self.site_config_path = self.get_platform_specific_path()

        # Save updated config to platform-specific path
        with open(self.site_config_path, "w") as file:
            json.dump(site_config, file, indent=4)

        # Done with bootstrap
        self.needs_bootstrap = False

    def _load_config(self) -> Dict[str, Any]:
        """Internal: Load configuration based on the SAGEWORKS_CONFIG environment variable.

        Returns:
            Dict[str, Any]: Configuration dictionary.
        """

        # Load site_config_path from environment variable
        self.site_config_path = os.environ.get("SAGEWORKS_CONFIG")
        if self.site_config_path is None:
            log.warning("SAGEWORKS_CONFIG ENV var not set. Using bootstrap configuration...")
            return self._load_bootstrap_config()

        # Load configuration from AWS Parameter Store
        if self.site_config_path == "parameter_store":
            try:
                log.info("Loading site configuration from AWS Parameter Store...")
                return self.get_config_from_aws_parameter_store()
            except Exception:
                log.error("Failed to load config from AWS Parameter Store. Using bootstrap...")
                return self._load_bootstrap_config()

        # Load site specified configuration file
        try:
            log.info(f"Loading site configuration from {self.site_config_path}...")
            with open(self.site_config_path, "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            log.error(f"Failed to load config from {self.site_config_path}. Using bootstrap...")
            return self._load_bootstrap_config()

    def _load_bootstrap_config(self) -> Dict[str, Any]:
        """Internal: Load the bootstrap configuration from the package resources.

        Returns:
            Dict[str, Any]: Bootstrap configuration dictionary.
        """
        self.needs_bootstrap = True
        with resources.open_text("sageworks.resources", "bootstrap_config.json") as file:
            return json.load(file)

    @staticmethod
    def get_platform_specific_path() -> str:
        """Returns the platform-specific path for the config file.

        Returns:
            str: Path for the config file.
        """
        home_dir = os.path.expanduser("~")
        config_file_name = "sageworks_config.json"

        if platform.system() == "Windows":
            # Use AppData\Local
            config_path = os.path.join(home_dir, "AppData", "Local", "SageWorks", config_file_name)
        else:
            # For macOS and Linux, use a hidden file in the home directory
            config_path = os.path.join(home_dir, ".sageworks", config_file_name)

        # Ensure the directory exists and return the path
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        return config_path

    def get_config_from_aws_parameter_store(self) -> Dict[str, Any]:
        """Stub method to fetch configuration from AWS Parameter Store.

        Returns:
            Dict[str, Any]: Configuration dictionary from AWS Parameter Store.
        """
        # TODO: Implement AWS Parameter Store fetching logic
        return {}

    def platform_specific_instructions(self):
        """Provides instructions to the user for setting the SAGEWORKS_CONFIG
        environment variable permanently based on their operating system.
        """
        os_name = platform.system()

        if os_name == "Windows":
            instructions = (
                "\nTo set the SAGEWORKS_CONFIG environment variable permanently on Windows:\n"
                "1. Press Win + R, type 'sysdm.cpl', and press Enter.\n"
                "2. Go to the 'Advanced' tab and click on 'Environment Variables'.\n"
                "3. Under 'System variables', click 'New'.\n"
                "4. Set 'Variable name' to 'SAGEWORKS_CONFIG' and 'Variable value' to '{}'.\n"
                "5. Click OK and Apply. You might need to restart your system for changes to take effect."
            ).format(self.site_config_path)

        elif os_name in ["Linux", "Darwin"]:  # Darwin is macOS
            shell_files = {"Linux": "~/.bashrc or ~/.profile", "Darwin": "~/.bash_profile, ~/.zshrc, or ~/.profile"}
            instructions = (
                "\nTo set the SAGEWORKS_CONFIG environment variable permanently on {}:\n"
                "1. Open {} in a text editor.\n"
                "2. Add the following line at the end of the file:\n"
                "   export SAGEWORKS_CONFIG='{}'\n"
                "3. Save the file and restart your terminal for the changes to take effect."
            ).format(os_name, shell_files[os_name], self.site_config_path)

        else:
            instructions = f"OS not recognized. Set the SAGEWORKS_CONFIG ENV var to {self.site_config_path} manually."

        print(instructions)


if __name__ == "__main__":
    """Exercise the ConfigManager class"""
    config_manager = ConfigManager()
    sageworks_role = config_manager.get_config("SAGEWORKS_ROLE")
    print(f"SAGEWORKS_ROLE: {sageworks_role}")
    sageworks_plugins = config_manager.get_config("SAGEWORKS_PLUGINS")
    print(f"SAGEWORKS_PLUGINS: {sageworks_plugins}")
