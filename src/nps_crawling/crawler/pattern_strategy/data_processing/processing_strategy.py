from abc import ABC, abstractmethod

class ProcessingStrategy(ABC):

    @abstractmethod
    def extract(self, response) -> str:
        pass