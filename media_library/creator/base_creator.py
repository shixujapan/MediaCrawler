from abc import ABC, abstractmethod

class BaseCreator(ABC):
    def __init__(self):
        """Initialize the base creator."""
        pass

    @abstractmethod
    def create(self):
        pass