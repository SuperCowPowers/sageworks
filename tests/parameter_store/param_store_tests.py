"""Tests for the SageWorks Parameter Store functionality"""

import logging

# SageWorks Imports
from sageworks.api import ParameterStore

# Show debug calls
logging.getLogger("sageworks").setLevel(logging.DEBUG)


def test_listing_values():
    param_store = ParameterStore()
    print("Listing Parameters...")
    print(param_store.list())


def test_simple_values():
    param_store = ParameterStore()

    # String
    param_store.add("test", "value", overwrite=True)
    return_value = param_store.get("test")
    assert return_value == "value"

    # Integer
    param_store.add("test", 42, overwrite=True)
    return_value = param_store.get("test")
    assert return_value == 42

    # Float
    param_store.add("test", 4.20, overwrite=True)
    return_value = param_store.get("test")
    assert return_value == 4.20


def test_lists():
    param_store = ParameterStore()

    # List of Strings
    value = ["a", "b", "c"]
    param_store.add("test", value, overwrite=True)
    return_value = param_store.get("test")
    assert return_value == value

    # List of Ints
    value = [1, 2, 3]
    param_store.add("test", value, overwrite=True)
    return_value = param_store.get("test")
    assert return_value == value


def test_dicts():
    param_store = ParameterStore()

    # Dictionary with values of strings, lists, integers and floats
    value = {"key": "str_value", "number": 42, "list": [1, 2, 3], "float": 3.14}
    param_store.add("my_data", value, overwrite=True)
    return_value = param_store.get("my_data")
    assert return_value == value


def test_deletion():
    param_store = ParameterStore()
    param_store.delete("test")
    param_store.delete("my_data")


def test_4k_limit():
    param_store = ParameterStore()

    # Create some data that will exceed the 4KB limit
    large_value = {"key": "x" * 5000}

    # Try adding a parameter that exceeds the 4KB limit
    param_store.add("test_large_value", large_value, overwrite=True)

    # Retrieve the parameter
    return_value = param_store.get("test_large_value")
    assert return_value == large_value


def test_compressed_failure():
    from random import random

    param_store = ParameterStore()

    # Create some data that will exceed the 4KB limit even after compression
    large_incompressible_value = [random() for _ in range(500)]

    try:
        # Try adding a parameter that exceeds the 4KB limit
        param_store.add("large_incompressible_value", large_incompressible_value, overwrite=True)
    except Exception as e:
        print("Caught expected Exception:", e)


if __name__ == "__main__":

    # Run the tests
    test_listing_values()
    test_simple_values()
    test_lists()
    test_dicts()
    test_deletion()
    test_4k_limit()
    test_compressed_failure()
