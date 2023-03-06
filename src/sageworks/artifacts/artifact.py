"""Artifact: Abstract Base Class for all stored entities in SageWorks"""
from abc import ABC, abstractmethod
from datetime import datetime


class Artifact(ABC):
    def __init__(self):
        """Artifact: Abstract Base Class for all stored entities in SageWorks"""

    @abstractmethod
    def check(self) -> bool:
        """Does the Artifact exist? Can we connect to it?"""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return the size of this artifact in MegaBytes"""
        pass

    @abstractmethod
    def created(self) -> datetime:
        """Return the datetime when this artifact was created"""
        pass

    @abstractmethod
    def modified(self) -> datetime:
        """Return the datetime when this artifact was last modified"""
        pass

    @abstractmethod
    def meta(self):
        """Get the metadata for this artifact"""
        pass

    @abstractmethod
    def tags(self):
        """Get the tags for this artifact"""
        pass

    @abstractmethod
    def add_tag(self, tag):
        """Add a tag to this artifact"""
        pass
