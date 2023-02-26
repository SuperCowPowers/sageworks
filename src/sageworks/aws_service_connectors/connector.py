"""Connector: Abstract Base Class for pulling/refreshing AWS Service metadata"""
from abc import ABC, abstractmethod


class Connector(ABC):
    """Connector: Abstract Base Class for pulling/refreshing AWS Service metadata"""
    def __init__(self):
        pass

    @abstractmethod
    def check(self) -> bool:
        """Can we connect to this service?"""
        pass

    @abstractmethod
    def refresh(self) -> bool:
        """Refresh data/metadata associated with this service"""
        pass

    @abstractmethod
    def get_data(self) -> dict:
        """Return all the data for this service"""
        pass
